import aiohttp
import jwt
from starlette.responses import RedirectResponse

from joj.horse.utils.fastapi import APIRouter, Request, HTTPException

from joj.horse.utils.oauth import jaccount
from joj.horse.utils.url import generate_url
from joj.horse.utils.session import set_session

from joj.horse.models.user import create_by_jaccount

router = APIRouter()
router_name = "user"
router_prefix = "/api/v1"


@router.get("/jaccount/login")
async def jaccount_login(request: Request):
    client = jaccount.get_client()
    if client is None:
        raise HTTPException(status_code=400, detail="Jaccount not supported")
    redirect_url = generate_url(router_prefix, router_name, "jaccount", "auth")
    url, state = client.get_authorize_url(redirect_url)
    request.session.oauth_state = state
    await set_session(request.session)
    return {"redirect_url": url}


@router.get("/jaccount/auth")
async def jaccount_auth(request: Request, state: str, code: str):
    client = jaccount.get_client()
    if client is None:
        raise HTTPException(status_code=400, detail="Jaccount not supported")
    if request.session.oauth_state != state:
        raise HTTPException(status_code=400, detail="Invalid authentication state")

    redirect_url = generate_url(router_prefix, router_name, "jaccount", "auth")
    token_url, headers, body = client.get_token_url(code=code, redirect_url=redirect_url)

    try:
        async with aiohttp.ClientSession() as http:
            async with http.post(token_url, headers=headers, data=body.encode("utf-8")) as response:
                data = await response.json()
                parsed_data = jwt.decode(data['id_token'], verify=False)
                id_token = jaccount.IDToken(**parsed_data)
    except:
        raise HTTPException(status_code=400, detail="Jaccount authentication failed")

    # print(id_token)
    # request.session.oauth_state = ''
    # request.session.name = id_token.name
    # request.session.uid = id_token.sub

    await create_by_jaccount(
        student_id=id_token.code,
        jaccount_name=id_token.sub,
        real_name=id_token.name,
        ip=request.client.host,
    )

    # await set_session(request.session)

    redirect_url = generate_url()
    return RedirectResponse(redirect_url)
