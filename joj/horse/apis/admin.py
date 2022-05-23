from typing import List, Optional

from fastapi import Depends, Query
from fastapi_jwt_auth import AuthJWT
from lakefs_client.models import CredentialsWithSecret
from sqlmodel import select
from starlette.concurrency import run_in_threadpool

from joj.horse import models, schemas
from joj.horse.models.permission import DefaultRole
from joj.horse.schemas.auth import Authentication, auth_jwt_encode_user
from joj.horse.schemas.base import StandardListResponse, StandardResponse
from joj.horse.services.lakefs import ensure_credentials, ensure_user
from joj.horse.utils.errors import ForbiddenError
from joj.horse.utils.fastapi.router import MyRouter
from joj.horse.utils.parser import (
    parse_ordering_query,
    parse_pagination_query,
    parse_uid,
    parse_uid_detail,
)


def ensure_site_root(auth: Authentication = Depends()) -> None:
    if not auth.is_root():
        raise ForbiddenError(message="site root Permission Denied.")


router = MyRouter(dependencies=[Depends(ensure_site_root)])
router_name = "admin"
router_tag = "admin"


@router.get("/users")
async def list_users(
    ordering: schemas.OrderingQuery = Depends(parse_ordering_query()),
    pagination: schemas.PaginationQuery = Depends(parse_pagination_query),
) -> StandardListResponse[schemas.User]:
    statement = select(models.User)
    users, count = await models.User.execute_list_statement(
        statement, ordering, pagination
    )
    return StandardListResponse(users, count)


@router.get("/{uid}")
async def get_user(
    user: models.User = Depends(parse_uid_detail),
) -> StandardResponse[schemas.UserDetail]:
    return StandardResponse(user)


@router.get("/{uid}/domains")
async def list_user_domains(
    role: Optional[List[str]] = Query(None),
    groups: Optional[List[str]] = Query(None),
    ordering: schemas.OrderingQuery = Depends(parse_ordering_query()),
    pagination: schemas.PaginationQuery = Depends(parse_pagination_query),
    user: models.User = Depends(parse_uid),
) -> StandardListResponse[schemas.Domain]:
    statement = user.find_domains_statement(role, groups)
    domains, count = await models.Domain.execute_list_statement(
        statement, ordering, pagination
    )
    return StandardListResponse(domains, count)


@router.get("/domain_roles")
async def list_domain_roles(
    ordering: schemas.OrderingQuery = Depends(parse_ordering_query()),
    pagination: schemas.PaginationQuery = Depends(parse_pagination_query),
) -> StandardListResponse[schemas.DomainRole]:
    statement = select(models.DomainRole)
    domain_roles, count = await models.DomainRole.execute_list_statement(
        statement, ordering, pagination
    )
    return StandardListResponse(domain_roles, count)


@router.get("/judgers")
async def list_judgers(
    ordering: schemas.OrderingQuery = Depends(parse_ordering_query()),
    pagination: schemas.PaginationQuery = Depends(parse_pagination_query),
) -> StandardListResponse[schemas.User]:
    statement = select(models.User).where(models.User.role == DefaultRole.JUDGER)
    users, count = await models.User.execute_list_statement(
        statement, ordering, pagination
    )
    return StandardListResponse(users, count)


@router.post("/judgers")
async def create_judger(
    judger_create: schemas.JudgerCreate,
    auth_jwt: AuthJWT = Depends(AuthJWT),
) -> schemas.StandardResponse[schemas.AuthTokensWithLakefs]:
    user = await models.User.create_judger(judger_create)
    access_token, refresh_token = auth_jwt_encode_user(auth_jwt, user=user)

    def sync_func() -> CredentialsWithSecret:
        ensure_user(user.username)
        return ensure_credentials(user.username)

    credentials = await run_in_threadpool(sync_func)

    return schemas.StandardResponse(
        schemas.AuthTokensWithLakefs(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            access_key_id=credentials.access_key_id,
            secret_access_key=credentials.secret_access_key,
        )
    )
