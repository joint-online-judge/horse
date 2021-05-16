from fastapi import Depends, Response

from joj.horse import models, schemas
from joj.horse.models.permission import DefaultRole
from joj.horse.schemas.base import Empty, StandardResponse
from joj.horse.schemas.domain_role import ListDomainRoles
from joj.horse.schemas.domain_user import ListDomainMembers
from joj.horse.schemas.user import ListUsers
from joj.horse.utils.auth import Authentication
from joj.horse.utils.errors import ForbiddenError
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
    a = 1 / 0
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
