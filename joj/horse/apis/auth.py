from datetime import datetime, timezone
from typing import Any, List, Literal, Optional, Tuple
from urllib.parse import quote_plus

from fastapi import Depends, HTTPException, Query, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi_jwt_auth import AuthJWT
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.config import settings
from joj.horse.utils.auth import (
    AuthParams,
    JWTAccessToken,
    JWTToken,
    auth_jwt_decode_access_token,
    auth_jwt_decode_access_token_optional,
    auth_jwt_decode_oauth_state,
    auth_jwt_decode_refresh_token,
    auth_jwt_encode_oauth_state,
    auth_jwt_encode_user,
    auth_jwt_raw_access_token,
    auth_jwt_raw_refresh_token,
)
from joj.horse.utils.oauth import BaseOAuth2, OAuth2Dependency, OAuth2Token
from joj.horse.utils.oauth.github import GitHubOAuth2
from joj.horse.utils.oauth.jaccount import JaccountOAuth2
from joj.horse.utils.router import MyRouter
from joj.horse.utils.url import get_base_url

router = MyRouter()
router_name = "auth"
router_tag = "auth"
router_prefix = "/api/v1"


# @camelcase_parameters
def auth_parameters_dependency(
    cookie: bool = Query(True, description="Add Set/Delete-Cookie on response header"),
    response_type: Literal["redirect", "json"] = Query(...),
    redirect_url: Optional[str] = Query(
        None, description="The redirect url after the operation"
    ),
) -> AuthParams:
    return AuthParams(
        cookie=cookie, response_type=response_type, redirect_url=redirect_url
    )


def set_redirect_response(response: Response, redirect_url: Optional[str]) -> bool:
    if redirect_url:
        response.status_code = 302
        response.headers["location"] = quote_plus(
            str(redirect_url), safe=":/%#?&=@[]!$&'()*+,;"
        )
        return True
    return False


async def get_login_response(
    request: Request,
    response: Response,
    auth_jwt: AuthJWT,
    parameters: AuthParams,
    access_token: str,
    refresh_token: str,
) -> Any:
    if parameters.cookie:
        if access_token:
            auth_jwt.set_access_cookies(access_token, response)
        if refresh_token:
            auth_jwt.set_refresh_cookies(refresh_token, response)
    if parameters.response_type == "json":
        return schemas.StandardResponse(
            schemas.AuthTokens(
                access_token=access_token,
                refresh_token=refresh_token,
                token_type="bearer",
            )
        )
    if parameters.response_type == "redirect":
        redirect_url = parameters.redirect_url or str(get_base_url(request))
        if set_redirect_response(response, redirect_url):
            return None
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)


async def get_logout_response(
    request: Request,
    response: Response,
    auth_jwt: AuthJWT,
    parameters: AuthParams,
    oauth_name: Optional[str],
) -> Any:
    if parameters.cookie:
        auth_jwt.unset_jwt_cookies(response)
    if parameters.response_type == "json":
        return schemas.StandardResponse()
    if parameters.response_type == "redirect":
        for oauth_client in _oauth_clients:
            if oauth_client.name == oauth_name:
                pass  # TODO: oauth logout
        redirect_url = parameters.redirect_url or str(get_base_url(request))
        if set_redirect_response(response, redirect_url):
            return None
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)


def get_oauth_router(
    oauth_clients: List[BaseOAuth2],
    # backend: BaseAuthentication,
    callback_redirect_url: Optional[str] = None,
) -> MyRouter:
    oauth_router = MyRouter()
    authorize_route_name = "oauth_authorize"
    callback_route_name = "oauth_callback"

    if callback_redirect_url is not None:
        oauth2_dependency = OAuth2Dependency(
            oauth_clients,
            redirect_url=callback_redirect_url,
        )
    else:
        oauth2_dependency = OAuth2Dependency(
            oauth_clients,
            route_name=callback_route_name,
        )

    @oauth_router.get("")
    async def list_oauth2() -> schemas.StandardListResponse[schemas.OAuth2Client]:
        result = [
            schemas.OAuth2Client(
                oauth_name=oauth_client.name,
                display_name=oauth_client.display_name,
                icon=oauth_client.icon,
            )
            for oauth_client in oauth_clients
        ]
        return schemas.StandardListResponse(result)

    @oauth_router.get("/{oauth2}/authorize", name=authorize_route_name)
    async def authorize(
        request: Request,
        oauth_client: BaseOAuth2 = Depends(oauth2_dependency.oauth_client()),
        auth_parameters: AuthParams = Depends(auth_parameters_dependency),
        auth_jwt: AuthJWT = Depends(AuthJWT),
        scopes: List[str] = Query(None),
    ) -> schemas.StandardResponse[schemas.Redirect]:
        if callback_redirect_url is not None:
            authorize_redirect_url = callback_redirect_url
        else:
            authorize_redirect_url = request.url_for(
                callback_route_name, oauth2=oauth_client.name
            )

        state_data = {"auth_parameters": auth_parameters.dict()}
        state = auth_jwt_encode_oauth_state(auth_jwt, oauth_client.name, state_data)
        authorization_url = await oauth_client.get_authorization_url(
            authorize_redirect_url,
            state,
            scopes,
        )
        return schemas.StandardResponse(
            schemas.Redirect(redirect_url=authorization_url)
        )

    @oauth_router.get(
        "/{oauth2}/callback", name=callback_route_name, include_in_schema=False
    )
    async def callback(
        request: Request,
        response: Response,
        oauth_client: BaseOAuth2 = Depends(oauth2_dependency.oauth_client()),
        auth_jwt: AuthJWT = Depends(AuthJWT),
        access_token_state: Tuple[OAuth2Token, Optional[str]] = Depends(
            oauth2_dependency.access_token_state()
        ),
    ) -> schemas.StandardResponse[schemas.AuthTokens]:
        try:
            token, state = access_token_state
            logger.info(token)
            oauth_profile, _ = await oauth_client.get_profile(token)
            state_data = auth_jwt_decode_oauth_state(auth_jwt, state)
        except Exception as e:
            logger.exception(e)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

        if not state_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)

        oauth_account = await models.UserOAuthAccount.create_or_update(
            oauth_client.name, token, oauth_profile
        )
        logger.info(oauth_account)

        if not oauth_account.user_id:
            access_token, refresh_token = auth_jwt_encode_user(
                auth_jwt, oauth=oauth_profile
            )
        else:
            user = await models.User.get_or_none(id=oauth_account.user_id)
            user.login_at = datetime.now(tz=timezone.utc)
            user.login_ip = request.client.host
            await user.save_model()
            logger.info("user oauth login: %s", user)

            access_token, refresh_token = auth_jwt_encode_user(
                auth_jwt, user=user, oauth_name=oauth_profile.oauth_name
            )

        return await get_login_response(
            request,
            response,
            auth_jwt,
            state_data.auth_parameters,
            access_token,
            refresh_token,
        )

    return oauth_router


@router.post("/login")
async def login(
    request: Request,
    response: Response,
    auth_parameters: AuthParams = Depends(auth_parameters_dependency),
    auth_jwt: AuthJWT = Depends(AuthJWT),
    credentials: OAuth2PasswordRequestForm = Depends(),
) -> schemas.StandardResponse[schemas.AuthTokens]:
    user = await models.User.get_or_none(username=credentials.username)
    user.login_at = datetime.now(tz=timezone.utc)
    user.login_ip = request.client.host
    await user.save_model()
    logger.info("user login: %s", user)
    access_token, refresh_token = auth_jwt_encode_user(auth_jwt, user=user)
    return await get_login_response(
        request, response, auth_jwt, auth_parameters, access_token, refresh_token
    )

    # raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST)


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    auth_parameters: AuthParams = Depends(auth_parameters_dependency),
    auth_jwt: AuthJWT = Depends(AuthJWT),
    jwt_access_token: JWTAccessToken = Depends(auth_jwt_decode_access_token),
) -> Any:
    oauth = jwt_access_token.oauth_name
    return await get_logout_response(
        request, response, auth_jwt, auth_parameters, oauth
    )


@router.post("/register")
async def register(
    request: Request,
    response: Response,
    user_create: models.UserCreate,
    auth_parameters: AuthParams = Depends(auth_parameters_dependency),
    auth_jwt: AuthJWT = Depends(AuthJWT),
    jwt_access_token: Optional[JWTAccessToken] = Depends(
        auth_jwt_decode_access_token_optional
    ),
) -> schemas.StandardResponse[schemas.AuthTokens]:
    if jwt_access_token is not None and jwt_access_token.category == "user":
        jwt_access_token = None
        # raise BizError(
        #     ErrorCode.UserRegisterError,
        #     "user already login, please logout before register",
        # )
    user_model = await models.User.create(
        user_create=user_create,
        jwt_access_token=jwt_access_token,
        register_ip=request.client.host,
    )
    access_token, refresh_token = auth_jwt_encode_user(
        auth_jwt, user=user_model, oauth_name=user_create.oauth_name
    )
    return await get_login_response(
        request, response, auth_jwt, auth_parameters, access_token, refresh_token
    )


@router.get("/token")
async def get_token(
    request: Request,
    response: Response,
    auth_parameters: AuthParams = Depends(auth_parameters_dependency),
    auth_jwt: AuthJWT = Depends(AuthJWT),
    access_token: str = Depends(auth_jwt_raw_access_token),
    refresh_token: str = Depends(auth_jwt_raw_refresh_token),
) -> schemas.StandardResponse[schemas.AuthTokens]:
    return await get_login_response(
        request,
        response,
        auth_jwt,
        auth_parameters,
        access_token,
        refresh_token,
    )


@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    auth_parameters: AuthParams = Depends(auth_parameters_dependency),
    auth_jwt: AuthJWT = Depends(AuthJWT),
    jwt_refresh_token: JWTToken = Depends(auth_jwt_decode_refresh_token),
) -> schemas.StandardResponse[schemas.AuthTokens]:
    user = await models.User.get_or_none(id=jwt_refresh_token.id)
    if user is None:
        access_token, refresh_token = "", ""
    else:
        access_token, refresh_token = auth_jwt_encode_user(
            auth_jwt, user=user, fresh=False
        )
    return await get_login_response(
        request, response, auth_jwt, auth_parameters, access_token, refresh_token
    )


_oauth_clients: List[BaseOAuth2] = []

if settings.oauth_jaccount:
    _oauth_clients.append(
        JaccountOAuth2(settings.oauth_jaccount_id, settings.oauth_jaccount_secret)
    )

if settings.oauth_github:
    _oauth_clients.append(
        GitHubOAuth2(settings.oauth_github_id, settings.oauth_github_secret)
    )

for _oauth_client in _oauth_clients:
    router.include_router(
        get_oauth_router(_oauth_clients),
        prefix="/oauth2",
    )
