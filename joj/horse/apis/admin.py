from http import HTTPStatus
from typing import List

from fastapi import Depends, Response

from joj.horse import models, schemas
from joj.horse.models.permission import DefaultRole
from joj.horse.utils.auth import Authentication
from joj.horse.utils.errors import ForbiddenError
from joj.horse.utils.parser import parse_uid
from joj.horse.utils.router import MyRouter

router = MyRouter()
router_name = "admin"
router_tag = "admin"
router_prefix = "/api/v1"


@router.get("/users")
async def list_users(auth: Authentication = Depends(),) -> List[schemas.User]:
    if auth.user.role != DefaultRole.ROOT:
        raise ForbiddenError()
    return [schemas.User.from_orm(user) async for user in models.User.find()]


@router.post("/users")
async def create_user(
    student_id: str,
    jaccount_name: str,
    real_name: str,
    ip: str,
    auth: Authentication = Depends(),
) -> schemas.User:
    if auth.user.role != DefaultRole.ROOT:
        raise ForbiddenError()
    user = await models.User.login_by_jaccount(
        student_id=student_id, jaccount_name=jaccount_name, real_name=real_name, ip=ip
    )
    assert user is not None
    return schemas.User.from_orm(user)


@router.delete(
    "/users/{uid}", status_code=HTTPStatus.NO_CONTENT, response_class=Response
)
async def delete_user(
    user: models.User = Depends(parse_uid), auth: Authentication = Depends()
) -> None:
    if auth.user.role != DefaultRole.ROOT:
        raise ForbiddenError()
    await user.delete()


@router.get("/domain_users")
async def list_domain_users(
    auth: Authentication = Depends(),
) -> List[schemas.DomainUser]:
    if auth.user.role != DefaultRole.ROOT:
        raise ForbiddenError()
    return [
        schemas.DomainUser.from_orm(domain_user)
        async for domain_user in models.DomainUser.find()
    ]


@router.get("/domain_roles")
async def list_domain_roles(
    auth: Authentication = Depends(),
) -> List[schemas.DomainRole]:
    if auth.user.role != DefaultRole.ROOT:
        raise ForbiddenError()
    return [
        schemas.DomainRole.from_orm(domain_role)
        async for domain_role in models.DomainRole.find()
    ]
