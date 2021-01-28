import aiohttp
import jose.jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi_jwt_auth import AuthJWT
from starlette.responses import RedirectResponse
from uvicorn.config import logger

from joj.horse.models.misc import RedirectModel
from joj.horse.models.user import login_by_jaccount
from joj.horse.utils.auth import Authentication, auth_jwt_encode
from joj.horse.utils.oauth import jaccount
from joj.horse.utils.url import generate_url

router = APIRouter()
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
                parsed_data = jose.jwt.get_unverified_claims(data["id_token"])
                id_token = jaccount.IDToken(**parsed_data)
    except:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Jaccount authentication failed")

    logger.info("Jaccount login: " + str(id_token))
    user = await login_by_jaccount(
        student_id=id_token.code,
        jaccount_name=id_token.sub,
        real_name=id_token.name,
        ip=request.client.host,
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Jaccount login failed")

    jwt = auth_jwt_encode(auth_jwt=auth_jwt, user=user, channel='jaccount')

    redirect_url = generate_url()
    logger.info(user)
    logger.info('jwt=%s', jwt)

    response = RedirectResponse(redirect_url)
    response.delete_cookie(key='jaccount_state')
    auth_jwt.set_access_cookies(jwt, response=response)
    return response


def get_jaccount_logout_url():
    client = jaccount.get_client()
    if client is None:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Jaccount not supported")
    redirect_url = generate_url()
    return client.get_logout_url(redirect_url)
