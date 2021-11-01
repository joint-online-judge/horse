"""
Modified based on https://github.com/frankie567/httpx-oauth
"""

import time
from typing import Any, Dict, Generic, List, Optional, Tuple, TypeVar, cast
from urllib.parse import urlencode

import httpx
from fastapi import Depends, HTTPException, Path
from pydantic import BaseModel
from starlette import status
from starlette.requests import Request


class HTTPXOAuthError(Exception):
    """Base exception class for every httpx-oauth errors."""

    pass


class GetProfileError(HTTPXOAuthError):
    """Error raised while retrieving user profile from provider API."""

    pass


class OAuth2Error(HTTPXOAuthError):
    """Base exception class for OAuth2 client errors."""

    pass


class RefreshTokenNotSupportedError(OAuth2Error):
    pass


class RevokeTokenNotSupportedError(OAuth2Error):
    pass


class GetAccessTokenError(OAuth2Error):
    pass


class RefreshTokenError(OAuth2Error):
    pass


class RevokeTokenError(OAuth2Error):
    pass


class OAuth2Token(Dict[str, Any]):
    def __init__(self, token_dict: Dict[str, Any]) -> None:
        if "expires_at" in token_dict:
            token_dict["expires_at"] = int(token_dict["expires_at"])
        elif "expires_in" in token_dict:
            token_dict["expires_at"] = int(time.time()) + int(token_dict["expires_in"])
        super().__init__(token_dict)

    def is_expired(self) -> bool:
        if "expires_at" not in self:
            return False
        return time.time() > self["expires_at"]


T = TypeVar("T")


class OAuth2Profile(BaseModel):
    oauth_name: str
    account_id: str
    account_name: str = ""
    account_email: str

    real_name: str = ""
    student_id: str = ""
    # raw_data: Dict[str, Any]


class BaseOAuth2(Generic[T]):

    name: str
    client_id: str
    client_secret: str
    authorize_endpoint: str
    access_token_endpoint: str
    refresh_token_endpoint: Optional[str]
    revoke_token_endpoint: Optional[str]
    base_scopes: Optional[List[str]]
    display_name: str
    request_headers: Dict[str, str]

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        authorize_endpoint: str,
        access_token_endpoint: str,
        refresh_token_endpoint: Optional[str] = None,
        revoke_token_endpoint: Optional[str] = None,
        name: str = "oauth2",
        base_scopes: Optional[List[str]] = None,
        display_name: Optional[str] = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.authorize_endpoint = authorize_endpoint
        self.access_token_endpoint = access_token_endpoint
        self.refresh_token_endpoint = refresh_token_endpoint
        self.revoke_token_endpoint = revoke_token_endpoint
        self.name = name
        self.base_scopes = base_scopes
        self.display_name = display_name or name

        self.request_headers = {
            "Accept": "application/json",
        }

    async def get_authorization_url(
        self,
        redirect_uri: str,
        state: str = None,
        scope: Optional[List[str]] = None,
        extras_params: Optional[T] = None,
    ) -> str:
        params = {
            "response_type": "code",
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
        }

        if state is not None:
            params["state"] = state

        if scope is not None:
            params["scope"] = " ".join(scope)

        if extras_params is not None:
            params = {**params, **extras_params}  # type: ignore

        return f"{self.authorize_endpoint}?{urlencode(params)}"

    async def get_access_token(self, code: str, redirect_uri: str) -> OAuth2Token:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.access_token_endpoint,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                headers=self.request_headers,
            )

            data = cast(Dict[str, Any], response.json())

            if response.status_code == 400:
                raise GetAccessTokenError(data)

            return OAuth2Token(data)

    async def refresh_token(self, refresh_token: str) -> OAuth2Token:
        if self.refresh_token_endpoint is None:
            raise RefreshTokenNotSupportedError()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.refresh_token_endpoint,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                headers=self.request_headers,
            )

            data = cast(Dict[str, Any], response.json())

            if response.status_code == 400:
                raise RefreshTokenError(data)

            return OAuth2Token(data)

    async def revoke_token(self, token: str, token_type_hint: str = None) -> None:
        if self.revoke_token_endpoint is None:
            raise RevokeTokenNotSupportedError()

        async with httpx.AsyncClient() as client:
            data = {"token": token}

            if token_type_hint is not None:
                data["token_type_hint"] = token_type_hint

            response = await client.post(
                self.revoke_token_endpoint, data=data, headers=self.request_headers
            )

            if response.status_code == 400:
                raise RevokeTokenError(response.json())

    async def get_profile(
        self, token: Dict[str, Any]
    ) -> Tuple[OAuth2Profile, Dict[str, Any]]:
        raise NotImplementedError()


OAuth2 = BaseOAuth2[Dict[str, Any]]


class OAuth2Dependency:

    oauth_clients: List[BaseOAuth2[Any]]
    route_name: Optional[str]
    redirect_url: Optional[str]

    def __init__(
        self,
        oauth_clients: List[BaseOAuth2[Any]],
        route_name: str = None,
        redirect_url: str = None,
    ) -> None:
        assert (route_name is not None and redirect_url is None) or (
            route_name is None and redirect_url is not None
        ), "You should either set route_name or redirect_url"
        self.oauth_clients = oauth_clients
        self.route_name = route_name
        self.redirect_url = redirect_url

    def oauth_client(self) -> Any:
        def func(
            oauth_name: str = Path(..., description="OAuth client name")
        ) -> BaseOAuth2[Any]:
            for oauth_client in self.oauth_clients:
                if oauth_name == oauth_client.name:
                    return oauth_client
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"OAuth client {oauth_name} not found!",
            )

        return func

    def access_token_state(self) -> Any:
        async def func(
            request: Request,
            oauth_client: BaseOAuth2[Any] = Depends(self.oauth_client()),
            code: str = None,
            state: str = None,
            error: str = None,
        ) -> Tuple[OAuth2Token, Optional[str]]:
            if code is None or error is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=error if error is not None else None,
                )

            if self.route_name:
                redirect_url = request.url_for(
                    self.route_name, oauth_name=oauth_client.name
                )
            elif self.redirect_url:
                redirect_url = self.redirect_url
            else:
                assert False

            access_token = await oauth_client.get_access_token(code, redirect_url)

            return access_token, state

        return func
