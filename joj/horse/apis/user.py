from typing import Union

import aiohttp
import jwt
from fastapi import Cookie, Depends, HTTPException, Query, Request, status
from fastapi_jwt_auth import AuthJWT
from starlette.responses import JSONResponse, RedirectResponse
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.schemas import StandardResponse
from joj.horse.schemas.domain import ListDomains
from joj.horse.schemas.misc import RedirectModel
from joj.horse.schemas.problem import ListProblems
from joj.horse.utils.auth import Authentication, auth_jwt_encode
from joj.horse.utils.errors import BadRequestError, BizError, ErrorCode
from joj.horse.utils.oauth import jaccount
from joj.horse.utils.parser import parse_query
from joj.horse.utils.router import MyRouter
from joj.horse.utils.url import generate_url

router = MyRouter()
router_name = "user"
router_tag = "user"
router_prefix = "/api/v1"


@router.get("/logout", response_model=RedirectModel)
async def logout(
    auth: Authentication = Depends(),
    auth_jwt: AuthJWT = Depends(),
    redirect_url: str = Query(
        generate_url(), description="Set the redirect url after the logout."
    ),
    redirect: bool = Query(
        True,
        description="If true (html link mode), redirect to a url; "
        "If false (ajax mode), return the redirect url, "
        "you also need to unset all cookies manually in ajax mode.",
    ),
) -> Union[RedirectResponse, JSONResponse]:
    if auth.jwt and auth.jwt.channel == "jaccount":
        url = get_jaccount_logout_url(redirect_url=redirect_url)
    else:
        url = redirect_url
    response: Union[RedirectResponse, JSONResponse]
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
) -> Union[RedirectResponse, JSONResponse]:
    client = jaccount.get_client()
    if client is None:
        raise BizError(ErrorCode.ApiNotImplementedError)

    jaccount_redirect_url = generate_url(router_prefix, router_name, "jaccount", "auth")
    url, state = client.get_authorize_url(jaccount_redirect_url)

    response: Union[RedirectResponse, JSONResponse]
    if redirect:
        response = RedirectResponse(url)
    else:
        response = JSONResponse({"redirect_url": url})
    response.set_cookie(key="jaccount_state", value=state)
    response.set_cookie(key="redirect_url", value=redirect_url)
    return response


@router.get("/jaccount/auth", response_model=RedirectModel)
async def jaccount_auth(
    request: Request,
    state: str,
    code: str,
    auth_jwt: AuthJWT = Depends(),
    jaccount_state: str = Cookie(""),
    redirect_url: str = Cookie(generate_url()),
) -> RedirectResponse:
    client = jaccount.get_client()
    if client is None:
        raise BizError(ErrorCode.ApiNotImplementedError)

    if jaccount_state != state:
        raise BadRequestError(message="Invalid authentication state")

    jaccount_redirect_url = generate_url(router_prefix, router_name, "jaccount", "auth")
    token_url, headers, body = client.get_token_url(
        code=code, redirect_url=jaccount_redirect_url
    )

    try:
        async with aiohttp.ClientSession() as http:
            async with http.post(
                token_url, headers=headers, data=body.encode("utf-8")
            ) as resp:
                data = await resp.json()
                parsed_data = jwt.decode(
                    data["id_token"], verify=False, options={"verify_signature": False}
                )
                id_token = jaccount.IDToken(**parsed_data)
    except Exception as e:
        logger.exception("Jaccount auth error")
        raise BadRequestError(message="Jaccount authentication failed")

    logger.info("Jaccount login: " + str(id_token))
    user = await models.User.login_by_jaccount(
        student_id=id_token.code,
        jaccount_name=id_token.sub,
        real_name=id_token.name,
        ip=request.client.host,
    )
    if user is None:
        raise BadRequestError(message="Jaccount login failed")

    access_jwt = auth_jwt_encode(auth_jwt=auth_jwt, user=user, channel="jaccount")

    logger.info(user)
    logger.info("jwt=%s", access_jwt)

    response = RedirectResponse(redirect_url)
    response.delete_cookie(key="jaccount_state")
    response.delete_cookie(key="redirect_url")
    auth_jwt.set_access_cookies(access_jwt, response=response)
    return response


def get_jaccount_logout_url(redirect_url: str) -> str:
    client = jaccount.get_client()
    if client is None:
        raise BizError(ErrorCode.ApiNotImplementedError)

    return client.get_logout_url(redirect_url)


@router.get("")
async def get_user(auth: Authentication = Depends()) -> StandardResponse[schemas.User]:
    return StandardResponse(schemas.User.from_orm(auth.user))


@router.get("/problems")
async def get_user_problems(
    query: schemas.BaseQuery = Depends(parse_query), auth: Authentication = Depends()
) -> StandardResponse[ListProblems]:
    condition = {"owner": auth.user.id}
    cursor = models.Problem.cursor_find(condition, query)
    res = await schemas.Problem.to_list(cursor)
    return StandardResponse(ListProblems(results=res))
