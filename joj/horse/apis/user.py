from typing import List, Union

import aiohttp
import jwt
from fastapi import Cookie, Depends, HTTPException, Query, Request, status
from fastapi_jwt_auth import AuthJWT
from fastapi_utils.inferring_router import InferringRouter
from starlette.responses import JSONResponse, RedirectResponse
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.schemas.misc import RedirectModel
from joj.horse.utils.auth import Authentication, auth_jwt_encode
from joj.horse.utils.oauth import jaccount
from joj.horse.utils.parser import parse_uid
from joj.horse.utils.url import generate_url

router = InferringRouter()
router_name = "user"
router_tag = "user"
router_prefix = "/api/v1"


@router.get("/logout", response_model=RedirectModel)
async def logout(
    auth: Authentication = Depends(Authentication),
    auth_jwt: AuthJWT = Depends(AuthJWT),
    redirect_url: str = Query(
        generate_url(), description="Set the redirect url after the logout."
    ),
    redirect: bool = Query(
        True,
        description="If true (html link mode), redirect to a url; "
        "If false (ajax mode), return the redirect url, "
        "you also need to unset all cookies manually in ajax mode.",
    ),
):
    if auth.jwt and auth.jwt.channel == "jaccount":
        url = get_jaccount_logout_url(redirect_url=redirect_url)
    else:
        url = redirect_url

    if redirect:
        response = RedirectResponse(url)
    else:
        response = JSONResponse({"redirect_url": url})
    auth_jwt.unset_access_cookies(response=response)
    return response


@router.get("/jaccount/login", response_model=RedirectModel)
async def jaccount_login(
    redirect_url: str = Query(
        generate_url(), description="Set the redirect url after the authorization."
    ),
    redirect: bool = Query(
        True,
        description="If true (html link mode), redirect to jaccount site; "
        "If false (ajax mode), return the redirect url to the jaccount site, "
        "you also need to set the cookies returned manually in ajax mode.",
    ),
) -> RedirectModel:
    client = jaccount.get_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Jaccount not supported"
        )
    jaccount_redirect_url = generate_url(router_prefix, router_name, "jaccount", "auth")
    url, state = client.get_authorize_url(jaccount_redirect_url)

    if redirect:
        response = RedirectResponse(url)
    else:
        response = JSONResponse({"redirect_url": url})
    response.set_cookie(key="jaccount_state", value=state)
    response.set_cookie(key="redirect_url", value=redirect_url)
    return response


@router.get("/jaccount/auth")
async def jaccount_auth(
    request: Request,
    state: str,
    code: str,
    auth_jwt: AuthJWT = Depends(AuthJWT),
    jaccount_state: str = Cookie(""),
    redirect_url: str = Cookie(generate_url()),
):
    client = jaccount.get_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Jaccount not supported"
        )
    if jaccount_state != state:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid authentication state",
        )

    jaccount_redirect_url = generate_url(router_prefix, router_name, "jaccount", "auth")
    token_url, headers, body = client.get_token_url(
        code=code, redirect_url=jaccount_redirect_url
    )

    try:
        async with aiohttp.ClientSession() as http:
            async with http.post(
                token_url, headers=headers, data=body.encode("utf-8")
            ) as response:
                data = await response.json()
                parsed_data = jwt.decode(data["id_token"], verify=False)
                id_token = jaccount.IDToken(**parsed_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Jaccount authentication failed",
        )

    logger.info("Jaccount login: " + str(id_token))
    user = await models.User.login_by_jaccount(
        student_id=id_token.code,
        jaccount_name=id_token.sub,
        real_name=id_token.name,
        ip=request.client.host,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Jaccount login failed"
        )

    access_jwt = auth_jwt_encode(auth_jwt=auth_jwt, user=user, channel="jaccount")

    logger.info(user)
    logger.info("jwt=%s", access_jwt)

    response = RedirectResponse(redirect_url)
    response.delete_cookie(key="jaccount_state")
    response.delete_cookie(key="redirect_url")
    auth_jwt.set_access_cookies(access_jwt, response=response)
    return response


def get_jaccount_logout_url(redirect_url) -> str:
    client = jaccount.get_client()
    if client is None:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Jaccount not supported"
        )
    return client.get_logout_url(redirect_url)


@router.get("", response_model=schemas.User)
async def get_user(
    user: models.User = Depends(parse_uid), auth: Authentication = Depends()
) -> schemas.User:
    return schemas.User.from_orm(user)


@router.get("/domains", response_model=List[schemas.Domain])
async def get_user_domains(auth: Authentication = Depends()) -> List[schemas.Domain]:
    return [
        schemas.Domain.from_orm(domain)
        async for domain in models.Domain.find({"owner": auth.user.id})
    ]


@router.get("/problems", response_model=List[schemas.Problem])
async def get_user_problems(auth: Authentication = Depends()) -> List[schemas.Problem]:
    return [
        schemas.Problem.from_orm(problem)
        async for problem in models.Problem.find({"owner": auth.user.id})
    ]
