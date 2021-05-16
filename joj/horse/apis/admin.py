from datetime import datetime

from fastapi import Depends
from fastapi_jwt_auth.auth_jwt import AuthJWT
from pydantic import EmailStr

from joj.horse import models, schemas
from joj.horse.models.permission import DefaultRole
from joj.horse.schemas.base import Empty, StandardResponse
from joj.horse.schemas.domain_role import ListDomainRoles
from joj.horse.schemas.domain_user import ListDomainMembers
from joj.horse.schemas.misc import JWT
from joj.horse.schemas.user import ListUsers
from joj.horse.utils.auth import (
    Authentication,
    auth_jwt_decode,
    auth_jwt_encode,
    jwt_token_encode,
)
from joj.horse.utils.errors import BizError, ErrorCode, ForbiddenError
from joj.horse.utils.parser import parse_query, parse_uid
from joj.horse.utils.router import MyRouter

router = MyRouter()
router_name = "admin"
router_tag = "admin"
router_prefix = "/api/v1"


@router.get("/users")
async def list_users(
    query: schemas.BaseFilter = Depends(parse_query), auth: Authentication = Depends()
) -> StandardResponse[ListUsers]:
    if auth.user.role != DefaultRole.ROOT:
        raise ForbiddenError()
    res = await schemas.User.to_list({}, query)
    return StandardResponse(ListUsers(results=res))


@router.post("/users")
async def create_user(
    student_id: str,
    jaccount_name: str,
    real_name: str,
    ip: str,
    auth: Authentication = Depends(),
) -> StandardResponse[schemas.User]:
    if auth.user.role != DefaultRole.ROOT:
        raise ForbiddenError()
    user = await models.User.login_by_jaccount(
        student_id=student_id, jaccount_name=jaccount_name, real_name=real_name, ip=ip
    )
    assert user is not None
    return StandardResponse(schemas.User.from_orm(user))


@router.delete("/users/{uid}")
async def delete_user(
    user: models.User = Depends(parse_uid), auth: Authentication = Depends()
) -> StandardResponse[Empty]:
    if auth.user.role != DefaultRole.ROOT:
        raise ForbiddenError()
    await user.delete()
    return StandardResponse()


@router.get("/domain_users")
async def list_domain_users(
    query: schemas.BaseFilter = Depends(parse_query), auth: Authentication = Depends()
) -> StandardResponse[ListDomainMembers]:
    if auth.user.role != DefaultRole.ROOT:
        raise ForbiddenError()
    res = await schemas.DomainUser.to_list({}, query)
    return StandardResponse(ListDomainMembers(results=res))


@router.get("/domain_roles")
async def list_domain_roles(
    query: schemas.BaseFilter = Depends(parse_query), auth: Authentication = Depends()
) -> StandardResponse[ListDomainRoles]:
    if auth.user.role != DefaultRole.ROOT:
        raise ForbiddenError()
    res = await schemas.DomainRole.to_list({}, query)
    return StandardResponse(ListDomainRoles(results=res))


@router.get("/judgers")
async def list_judgers(
    query: schemas.BaseFilter = Depends(parse_query), auth: Authentication = Depends()
) -> StandardResponse[ListUsers]:
    if auth.user.role != DefaultRole.ROOT:
        raise ForbiddenError()
    filter = {"role": DefaultRole.JUDGE}
    res = await schemas.User.to_list(filter, query)
    return StandardResponse(ListUsers(results=res))


@router.post("/judgers")
async def create_judger(
    uname: str, mail: EmailStr, auth: Authentication = Depends()
) -> StandardResponse[schemas.User]:
    if auth.user.role != DefaultRole.ROOT:
        raise ForbiddenError()
    user_schema = schemas.User(
        scope="sjtu",
        role=DefaultRole.JUDGE,
        uname=uname,
        mail=mail,
        register_timestamp=datetime.utcnow(),
        login_timestamp=datetime.utcnow(),
    )
    user = models.User(**user_schema.to_model())
    await user.commit()
    return StandardResponse(schemas.User.from_orm(user))


@router.get("/judgers/{uid}/jwt")
async def get_judger_jwt(
    user: models.User = Depends(parse_uid), auth: Authentication = Depends()
) -> JWT:
    if auth.user.role != DefaultRole.ROOT:
        raise ForbiddenError()
    if user.role != DefaultRole.JUDGE:
        raise BizError(ErrorCode.UserNotJudgerError)
    jwt = AuthJWT().create_access_token(
        subject=str(user.id),
        user_claims={"name": user.uname_lower, "scope": user.scope, "channel": "admin"},
        expires_time=False,
    )
    return JWT(jwt=jwt)
