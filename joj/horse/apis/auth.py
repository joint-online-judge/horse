from typing import Any, Dict, List, Optional, Tuple

from fastapi import Depends, HTTPException, Query, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_jwt_auth import AuthJWT
from uvicorn.config import logger

from joj.horse import models
from joj.horse.config import settings
from joj.horse.utils.auth import (
    JWTAccessToken,
    JWTToken,
    auth_jwt_decode_access_token,
    auth_jwt_decode_access_token_optional,
    auth_jwt_decode_oauth_state,
    auth_jwt_decode_refresh_token,
    auth_jwt_encode_oauth_state,
    auth_jwt_encode_user,
    auth_jwt_raw_token,
)
from joj.horse.utils.auth.backend import (
    BaseAuthentication,
    CookieAuthentication,
    JWTAuthentication,
)
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.oauth import BaseOAuth2, OAuth2AuthorizeCallback, OAuth2Token
from joj.horse.utils.oauth.github import GitHubOAuth2
from joj.horse.utils.oauth.jaccount import JaccountOAuth2
from joj.horse.utils.router import MyRouter

router = MyRouter()
router_name = "auth"
router_tag = "auth"
router_prefix = "/api/v1"


def get_oauth_router(
    oauth_client: BaseOAuth2,
    backend: BaseAuthentication,
    callback_redirect_url: Optional[str] = None,
) -> MyRouter:
    oauth_router = MyRouter()
    authorize_route_name = f"oauth_{oauth_client.name}_{backend.name}_authorize"
    callback_route_name = f"oauth_{oauth_client.name}_{backend.name}_callback"

    # if len(authentication_backends) == 0:
    #     raise SystemError("at least one authentication backend should be defined")

    if callback_redirect_url is not None:
        oauth2_authorize_callback = OAuth2AuthorizeCallback(
            oauth_client,
            redirect_url=callback_redirect_url,
        )
    else:
        oauth2_authorize_callback = OAuth2AuthorizeCallback(
            oauth_client,
            route_name=callback_route_name,
        )

    @oauth_router.get("/authorize", name=authorize_route_name)
    async def authorize(
        request: Request,
        auth_jwt: AuthJWT = Depends(AuthJWT),
        backend_parameters: Dict[str, Any] = Depends(
            backend.get_parameters_dependency()
        ),
        # redirect_url: Optional[str] = Query(
        #     None,
        #     description="Set the redirect url after the authorization. (for cookie authentication)",
        # ),
        # authentication_backend: str = Query(authentication_backends[0].name),
        scopes: List[str] = Query(None),
    ) -> Any:
        # backend_exists = any(
        #     backend.name == authentication_backend
        #     for backend in authentication_backends
        # )
        #
        # if not backend_exists:
        #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

        # if not redirect_url:
        #     redirect_url = str(get_base_url(request))

        if callback_redirect_url is not None:
            authorize_redirect_url = callback_redirect_url
        else:
            authorize_redirect_url = request.url_for(callback_route_name)

        state_data = {
            "authentication_backend": backend.name,
            "backend_parameters": backend_parameters,
        }
        state = auth_jwt_encode_oauth_state(auth_jwt, oauth_client.name, state_data)
        authorization_url = await oauth_client.get_authorization_url(
            authorize_redirect_url,
            state,
            scopes,
        )

        return {"authorization_url": authorization_url}

    @oauth_router.get("/callback", name=callback_route_name, include_in_schema=False)
    async def callback(
        request: Request,
        response: Response,
        auth_jwt: AuthJWT = Depends(AuthJWT),
        access_token_state: Tuple[OAuth2Token, Optional[str]] = Depends(
            oauth2_authorize_callback
        ),
    ) -> Any:
        try:
            token, state = access_token_state
            logger.info(token)
            oauth_profile, _ = await oauth_client.get_profile(token)
            state_data = auth_jwt_decode_oauth_state(auth_jwt, state)
        except Exception as e:
            logger.exception(e)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

        if not state_data or state_data.authentication_backend != backend.name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

        oauth_account = await models.UserOAuthAccount.create_or_update(
            oauth_client.name, token, oauth_profile
        )
        logger.info(oauth_account)
        # logger.info(oauth_profile)

        if not oauth_account.user_id:
            access_token, refresh_token = auth_jwt_encode_user(
                auth_jwt, oauth=oauth_profile
            )
        else:
            user = await models.User.get_or_none(id=oauth_account.user_id)
            access_token, refresh_token = auth_jwt_encode_user(
                auth_jwt, user=user, oauth_name=oauth_profile.oauth_name
            )

        return await backend.get_login_response(
            request,
            response,
            auth_jwt,
            access_token,
            refresh_token,
            state_data.backend_parameters,
        )

    return oauth_router


def get_auth_router(
    backend: BaseAuthentication,
    oauth_clients: List[BaseOAuth2],
) -> MyRouter:
    auth_router = MyRouter()

    @auth_router.post("/login")
    async def login(
        request: Request,
        response: Response,
        auth_jwt: AuthJWT = Depends(AuthJWT),
        credentials: OAuth2PasswordRequestForm = Depends(),
        backend_parameters: Dict[str, Any] = Depends(
            backend.get_parameters_dependency()
        ),
    ) -> Any:
        user = await models.User.get_or_none(id=credentials.username)
        access_token, refresh_token = auth_jwt_encode_user(auth_jwt, user=user)
        return await backend.get_login_response(
            request, response, auth_jwt, access_token, refresh_token, backend_parameters
        )

        # raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

    @auth_router.post("/logout")
    async def logout(
        request: Request,
        response: Response,
        auth_jwt: AuthJWT = Depends(AuthJWT),
        jwt_access_token: JWTAccessToken = Depends(auth_jwt_decode_access_token),
    ) -> Any:
        user = jwt_access_token.user
        oauth = jwt_access_token.oauth_name
        return await backend.get_logout_response(
            request, response, auth_jwt, user, oauth, {}
        )

    @auth_router.post("/register")
    async def register(
        request: Request,
        response: Response,
        user_create: models.UserCreate,
        auth_jwt: AuthJWT = Depends(AuthJWT),
        jwt_access_token: Optional[JWTAccessToken] = Depends(
            auth_jwt_decode_access_token_optional
        ),
        backend_parameters: Dict[str, Any] = Depends(
            backend.get_parameters_dependency()
        ),
    ) -> Any:
        if jwt_access_token is not None and jwt_access_token.category == "user":
            raise BizError(
                ErrorCode.UserRegisterError,
                "user already login, please logout before register",
            )
        user_model = await models.User.create(
            user_create=user_create,
            jwt_access_token=jwt_access_token,
            register_ip=request.client.host,
        )
        access_token, refresh_token = auth_jwt_encode_user(
            auth_jwt, user=user_model, oauth_name=user_create.oauth_name
        )
        return await backend.get_login_response(
            request, response, auth_jwt, access_token, refresh_token, backend_parameters
        )

    @auth_router.get("/token")
    async def get_token(
        request: Request,
        response: Response,
        auth_jwt: AuthJWT = Depends(AuthJWT),
        access_token: Optional[str] = Depends(auth_jwt_raw_token),
        backend_parameters: Dict[str, Any] = Depends(
            backend.get_parameters_dependency()
        ),
    ) -> Any:
        return await backend.get_login_response(
            request, response, auth_jwt, access_token, "", backend_parameters
        )

    @auth_router.get("/refresh")
    async def refresh(
        request: Request,
        response: Response,
        auth_jwt: AuthJWT = Depends(AuthJWT),
        jwt_refresh_token: JWTToken = Depends(auth_jwt_decode_refresh_token),
        backend_parameters: Dict[str, Any] = Depends(
            backend.get_parameters_dependency()
        ),
    ) -> Any:
        user = await models.User.get_or_none(id=jwt_refresh_token.id)
        if user is None:
            access_token, refresh_token = "", ""
        else:
            access_token, refresh_token = auth_jwt_encode_user(auth_jwt, user=user)
        return await backend.get_login_response(
            request, response, auth_jwt, access_token, refresh_token, backend_parameters
        )

    return auth_router


backends = [
    CookieAuthentication(),
    JWTAuthentication(),
]


oauth_clients = []

if settings.oauth_jaccount:
    oauth_clients.append(
        JaccountOAuth2(settings.oauth_jaccount_id, settings.oauth_jaccount_secret)
    )

if settings.oauth_github:
    oauth_clients.append(
        GitHubOAuth2(settings.oauth_github_id, settings.oauth_github_secret)
    )

for oauth_client in oauth_clients:
    for backend in backends:
        router.include_router(
            get_oauth_router(oauth_client, backend),
            prefix=f"/oauth/{oauth_client.name}/{backend.name}",
        )

for backend in backends:
    router.include_router(
        get_auth_router(backend, oauth_clients), prefix=f"/{backend.name}"
    )
