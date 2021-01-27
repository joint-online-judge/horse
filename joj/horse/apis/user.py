import aiohttp
import jose.jwt
from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import RedirectResponse
from uvicorn.config import logger

from joj.horse.models.user import login_by_jaccount
from joj.horse.utils.auth import Authentication, generate_jwt
from joj.horse.utils.oauth import jaccount
from joj.horse.utils.url import generate_url

router = APIRouter()
router_name = "user"
router_prefix = "/api/v1"


@router.get("/logout")
async def logout(auth: Authentication = Depends(Authentication)):
    url = ""
    if auth.jwt and auth.jwt.type == "jaccount":
        url = get_jaccount_logout_url()
    return {"redirect_url": url}


@router.get("/jaccount/login")
async def jaccount_login():
    client = jaccount.get_client()
    if client is None:
        raise HTTPException(status_code=400, detail="Jaccount not supported")
    redirect_url = generate_url(router_prefix, router_name, "jaccount", "auth")
    url, state = client.get_authorize_url(redirect_url)
    return {"redirect_url": url}


@router.get("/jaccount/auth")
async def jaccount_auth(request: Request, state: str, code: str):
    client = jaccount.get_client()
    if client is None:
        raise HTTPException(status_code=400, detail="Jaccount not supported")
    # if request.session.oauth_state != state:
    #     raise HTTPException(status_code=400, detail="Invalid authentication state")

    redirect_url = generate_url(router_prefix, router_name, "jaccount", "auth")
    token_url, headers, body = client.get_token_url(code=code, redirect_url=redirect_url)

    try:
        async with aiohttp.ClientSession() as http:
            async with http.post(token_url, headers=headers, data=body.encode("utf-8")) as response:
                data = await response.json()
                parsed_data = jose.jwt.get_unverified_claims(data["id_token"])
                id_token = jaccount.IDToken(**parsed_data)
    except:
        raise HTTPException(status_code=400, detail="Jaccount authentication failed")

    logger.info("Jaccount login: " + str(id_token))
    user = await login_by_jaccount(
        student_id=id_token.code,
        jaccount_name=id_token.sub,
        real_name=id_token.name,
        ip=request.client.host,
    )
    if user is None:
        raise HTTPException(status_code=400, detail="Duplicate")

    jwt = generate_jwt(user=user, type='jaccount')
    redirect_url = generate_url()
    logger.info(user)
    logger.info('jwt=%s', jwt)
    return RedirectResponse(redirect_url, headers={'JWT': jwt})


def get_jaccount_logout_url():
    client = jaccount.get_client()
    if client is None:
        raise HTTPException(status_code=400, detail="Jaccount not supported")
    redirect_url = generate_url()
    return client.get_logout_url(redirect_url)
