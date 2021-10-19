from typing import Any, List, Optional, Tuple

from fastapi import Depends, HTTPException, Query, Request, Response, status
from fastapi_jwt_auth import AuthJWT
from uvicorn.config import logger

from joj.horse import models
from joj.horse.config import settings
from joj.horse.utils.auth import (
    auth_jwt_decode_oauth_state,
    auth_jwt_encode_oauth_state,
)
from joj.horse.utils.auth.backend import (
    BaseAuthentication,
    CookieAuthentication,
    JWTAuthentication,
)
from joj.horse.utils.oauth import BaseOAuth2, OAuth2AuthorizeCallback, OAuth2Token
from joj.horse.utils.oauth.jaccount import JaccountOAuth2
from joj.horse.utils.router import MyRouter
from joj.horse.utils.url import get_base_url

router = MyRouter()
router_name = "auth"
router_tag = "auth"
router_prefix = "/api/v1"


def get_oauth_router(
    oauth_client: BaseOAuth2,
    authentication_backends: List[BaseAuthentication],
    callback_redirect_url: Optional[str] = None,
) -> MyRouter:
    router = MyRouter()
    callback_route_name = f"oauth-{oauth_client.name}-callback"

    if len(authentication_backends) == 0:
        raise SystemError("at least one authentication backend should be defined")

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

    @router.get("/authorize")
    async def authorize(
        request: Request,
        auth_jwt: AuthJWT = Depends(AuthJWT),
        redirect_url: Optional[str] = Query(
            None, description="Set the redirect url after the authorization."
        ),
        authentication_backend: str = Query(authentication_backends[0].name),
        scopes: List[str] = Query(None),
    ) -> Any:
        backend_exists = any(
            backend.name == authentication_backend
            for backend in authentication_backends
        )

        if not backend_exists:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

        if not redirect_url:
            redirect_url = str(get_base_url(request))

        if callback_redirect_url is not None:
            authorize_redirect_url = callback_redirect_url
        else:
            authorize_redirect_url = request.url_for(callback_route_name)

        state_data = {
            "authentication_backend": authentication_backend,
            "redirect_url": redirect_url,
        }
        state = auth_jwt_encode_oauth_state(auth_jwt, oauth_client.name, state_data)
        authorization_url = await oauth_client.get_authorization_url(
            authorize_redirect_url,
            state,
            scopes,
        )

        return {"authorization_url": authorization_url}

    @router.get("/callback", name=callback_route_name)
    async def callback(
        request: Request,
        response: Response,
        auth_jwt: AuthJWT = Depends(AuthJWT),
        access_token_state: Tuple[OAuth2Token, Optional[str]] = Depends(
            oauth2_authorize_callback
        ),
        # user_manager: BaseUserManager[models.UC, models.UD] = Depends(get_user_manager),
    ) -> Any:
        token, state = access_token_state
        profile, _ = await oauth_client.get_profile(token)

        try:
            state_data = auth_jwt_decode_oauth_state(auth_jwt, state)
        except Exception as e:
            logger.exception(e)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

        oauth_account = await models.UserOAuthAccount.create_or_update(
            oauth_client.name, token, profile
        )
        logger.info(oauth_account)
        # logger.info(profile)

        if not oauth_account.user_id:
            user = None
        else:
            user = await models.User.find_by_id(oauth_account.user_id)

        if state_data:
            for backend in authentication_backends:
                if backend.name == state_data.authentication_backend:
                    return await backend.get_login_response(
                        auth_jwt, user, profile, state_data.redirect_url, response
                    )

        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)
        # return response

        # new_oauth_account = models.BaseOAuthAccount(
        #     oauth_name=oauth_client.name,
        #     access_token=token["access_token"],
        #     expires_at=token.get("expires_at"),
        #     refresh_token=token.get("refresh_token"),
        #     account_id=account_id,
        #     account_email=account_email,
        # )
        #
        # user = await user_manager.oauth_callback(new_oauth_account, request)
        #
        # if not user.is_active:
        #     raise HTTPException(
        #         status_code=status.HTTP_400_BAD_REQUEST,
        #         detail=ErrorCode.LOGIN_BAD_CREDENTIALS,
        #     )
        #
        # # Authenticate
        # for backend in authenticator.backends:
        #     if backend.name == state_data["authentication_backend"]:
        #         return await backend.get_login_response(user, response, user_manager)

    return router


authentication_backends = [
    CookieAuthentication(),
    JWTAuthentication(),
]


if settings.oauth_jaccount:
    jaccount_oauth2 = JaccountOAuth2(
        settings.oauth_jaccount_id, settings.oauth_jaccount_secret
    )
    router.include_router(
        get_oauth_router(jaccount_oauth2, authentication_backends), prefix="/jaccount"
    )
