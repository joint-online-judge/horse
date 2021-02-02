import aiohttp
import jwt
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi_jwt_auth import AuthJWT
from fastapi_utils.inferring_router import InferringRouter
from starlette.responses import RedirectResponse
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.schemas.misc import RedirectModel
from joj.horse.utils import errors
from joj.horse.utils.auth import Authentication, auth_jwt_encode
from joj.horse.utils.oauth import jaccount
from joj.horse.utils.url import generate_url

router = InferringRouter()
router_name = "user"
router_prefix = "/api/v1"


@router.get("/logout", response_model=RedirectModel)
async def logout(auth: Authentication = Depends(Authentication), auth_jwt: AuthJWT = Depends(AuthJWT)):
    url = ""
    if auth.jwt and auth.jwt.channel == "jaccount":
        url = get_jaccount_logout_url()
    auth_jwt.unset_access_cookies()
    return {"redirect_url": url}


@router.get("/jaccount/login", response_model=RedirectModel)
async def jaccount_login(response: Response):
    client = jaccount.get_client()
    if client is None:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Jaccount not supported")
    redirect_url = generate_url(router_prefix, router_name, "jaccount", "auth")
    url, state = client.get_authorize_url(redirect_url)
    response.set_cookie(key='jaccount_state', value=state)
    return {"redirect_url": url}


@router.get("/jaccount/auth")
async def jaccount_auth(request: Request, state: str, code: str, auth_jwt: AuthJWT = Depends(AuthJWT)):
    client = jaccount.get_client()
    if client is None:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Jaccount not supported")
    if "jaccount_state" not in request.cookies or request.cookies["jaccount_state"] != state:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid authentication state")

    redirect_url = generate_url(router_prefix, router_name, "jaccount", "auth")
    token_url, headers, body = client.get_token_url(code=code, redirect_url=redirect_url)

    try:
        async with aiohttp.ClientSession() as http:
            async with http.post(token_url, headers=headers, data=body.encode("utf-8")) as response:
                data = await response.json()
                parsed_data = jwt.decode(data["id_token"], verify=False)
                id_token = jaccount.IDToken(**parsed_data)
    except Exception as e:
        print(e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Jaccount authentication failed")

    logger.info("Jaccount login: " + str(id_token))
    user = await models.User.login_by_jaccount(
        student_id=id_token.code,
        jaccount_name=id_token.sub,
        real_name=id_token.name,
        ip=request.client.host,
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Jaccount login failed")

    access_jwt = auth_jwt_encode(auth_jwt=auth_jwt, user=user, channel='jaccount')

    redirect_url = generate_url()
    logger.info(user)
    logger.info('jwt=%s', access_jwt)

    response = RedirectResponse(redirect_url)
    response.delete_cookie(key='jaccount_state')
    auth_jwt.set_access_cookies(access_jwt, response=response)
    return response


def get_jaccount_logout_url():
    client = jaccount.get_client()
    if client is None:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Jaccount not supported")
    redirect_url = generate_url()
    return client.get_logout_url(redirect_url)


async def parse_uid(uid: str, auth: Authentication = Depends()) -> models.User:
    if uid == "me":
        if auth.user:
            return auth.user
        raise errors.InvalidAuthenticationError()
    else:
        user = await models.User.find_by_id(uid)
        if user:
            return user
        raise errors.UserNotFoundError(uid)


@router.get('/{uid}')
async def get_user(user: models.User = Depends(parse_uid)) -> schemas.UserBase:
    return schemas.UserBase.from_orm(user)

# @router.get('/{uid}/domains', response_model=List[DomainUserResponse])
# async def get_user_domains(user: User = Depends(parse_uid)):
#     domains = []
#     async for domain in DomainUser.find({"user": user.id}):
#         domains.append(DomainUserResponse(**domain.dict()))
#     return domains
