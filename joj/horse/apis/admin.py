from datetime import datetime

from fastapi import Depends
from pydantic import EmailStr

from joj.horse import models, schemas
from joj.horse.models.permission import DefaultRole
from joj.horse.schemas.base import Empty, StandardListResponse, StandardResponse
from joj.horse.utils.auth import Authentication
from joj.horse.utils.errors import ForbiddenError
from joj.horse.utils.parser import parse_pagination_query, parse_uid
from joj.horse.utils.router import MyRouter

# TODO: site root router
router = MyRouter()
router_name = "admin"
router_tag = "admin"
router_prefix = "/api/v1"


@router.get("/users")
async def list_users(
    query: schemas.PaginationQuery = Depends(parse_pagination_query),
    auth: Authentication = Depends(),
) -> StandardListResponse[schemas.User]:
    if not auth.is_root():
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
) -> StandardResponse[schemas.User]:
    if not auth.is_root():
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
    if not auth.is_root():
        raise ForbiddenError()
    await user.delete_model()
    return StandardResponse()


# @router.get("/domain_users")
# async def list_domain_users(
#     query: schemas.PaginationQuery = Depends(parse_pagination_query),
#     auth: Authentication = Depends(),
# ) -> StandardListResponse[models.DomainUser]:
#     if not auth.is_root():
#         raise ForbiddenError()
#     cursor = models.DomainUser.cursor_find({}, query)
#     res = await models.DomainUser.to_list(cursor)
#     return StandardListResponse(res)


@router.get("/domain_roles")
async def list_domain_roles(
    query: schemas.PaginationQuery = Depends(parse_pagination_query),
    auth: Authentication = Depends(),
) -> StandardListResponse[schemas.DomainRole]:
    if not auth.is_root():
        raise ForbiddenError()
    cursor = models.DomainRole.cursor_find({}, query)
    res = await models.DomainRole.to_list(cursor)
    return StandardListResponse(res)


@router.get("/judgers")
async def list_judgers(
    query: schemas.PaginationQuery = Depends(parse_pagination_query),
    auth: Authentication = Depends(),
) -> StandardListResponse[schemas.User]:
    if not auth.is_root():
        raise ForbiddenError()
    condition = {"role": DefaultRole.JUDGE}
    cursor = models.User.cursor_find(condition, query)
    res = await models.User.to_list(cursor)
    return StandardListResponse(res)


@router.post("/judgers")
async def create_judger(
    uname: str, mail: EmailStr, auth: Authentication = Depends()
) -> StandardResponse[schemas.User]:
    if not auth.is_root():
        raise ForbiddenError()
    # TODO: scope
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
