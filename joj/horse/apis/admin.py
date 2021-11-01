from datetime import datetime, timedelta

from fastapi import Depends
from fastapi_jwt_auth.auth_jwt import AuthJWT
from pydantic import EmailStr

from joj.horse import models, schemas
from joj.horse.models.permission import DefaultRole
from joj.horse.schemas.base import Empty, StandardListResponse, StandardResponse
from joj.horse.schemas.misc import JWT
from joj.horse.utils.auth import Authentication
from joj.horse.utils.errors import BizError, ErrorCode, ForbiddenError
from joj.horse.utils.parser import parse_pagination_query, parse_uid
from joj.horse.utils.router import MyRouter

router = MyRouter()
router_name = "admin"
router_tag = "admin"
router_prefix = "/api/v1"


@router.get("/users")
async def list_users(
    query: schemas.PaginationQuery = Depends(parse_pagination_query),
    auth: Authentication = Depends(),
) -> StandardListResponse[models.UserBase]:
    if auth.user.role != DefaultRole.ROOT:
        raise ForbiddenError()
    cursor = models.User.cursor_find({}, query)
    res = await models.User.to_list(cursor)
    return StandardListResponse(res)


@router.post("/users")
async def create_user(
    student_id: str,
    jaccount_name: str,
    real_name: str,
    ip: str,
    auth: Authentication = Depends(),
) -> StandardResponse[models.User]:
    if auth.user.role != DefaultRole.ROOT:
        raise ForbiddenError()
    user = await models.User.login_by_jaccount(
        student_id=student_id, jaccount_name=jaccount_name, real_name=real_name, ip=ip
    )
    assert user is not None
    return StandardResponse(models.User.from_orm(user))


@router.delete("/users/{uid}")
async def delete_user(
    user: models.User = Depends(parse_uid), auth: Authentication = Depends()
) -> StandardResponse[Empty]:
    if auth.user.role != DefaultRole.ROOT:
        raise ForbiddenError()
    await user.delete_model()
    return StandardResponse()


@router.get("/domain_users")
async def list_domain_users(
    query: schemas.PaginationQuery = Depends(parse_pagination_query),
    auth: Authentication = Depends(),
) -> StandardListResponse[models.DomainUser]:
    if auth.user.role != DefaultRole.ROOT:
        raise ForbiddenError()
    cursor = models.DomainUser.cursor_find({}, query)
    res = await models.DomainUser.to_list(cursor)
    return StandardListResponse(res)


@router.get("/domain_roles")
async def list_domain_roles(
    query: schemas.PaginationQuery = Depends(parse_pagination_query),
    auth: Authentication = Depends(),
) -> StandardListResponse[models.DomainRole]:
    if auth.user.role != DefaultRole.ROOT:
        raise ForbiddenError()
    cursor = models.DomainRole.cursor_find({}, query)
    res = await models.DomainRole.to_list(cursor)
    return StandardListResponse(res)


@router.get("/judgers")
async def list_judgers(
    query: schemas.PaginationQuery = Depends(parse_pagination_query),
    auth: Authentication = Depends(),
) -> StandardListResponse[models.User]:
    if auth.user.role != DefaultRole.ROOT:
        raise ForbiddenError()
    condition = {"role": DefaultRole.JUDGE}
    cursor = models.User.cursor_find(condition, query)
    res = await models.User.to_list(cursor)
    return StandardListResponse(res)


@router.post("/judgers")
async def create_judger(
    uname: str, mail: EmailStr, auth: Authentication = Depends()
) -> StandardResponse[models.User]:
    if auth.user.role != DefaultRole.ROOT:
        raise ForbiddenError()
    user_schema = models.User(
        scope="sjtu",
        role=DefaultRole.JUDGE,
        uname=uname,
        mail=mail,
        register_timestamp=datetime.utcnow(),
        login_timestamp=datetime.utcnow(),
    )
    user = models.User(**user_schema.to_model())
    await user.commit()
    return StandardResponse(models.User.from_orm(user))


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
        expires_time=timedelta(days=365 * 10000),
    )
    return JWT(jwt=jwt)
