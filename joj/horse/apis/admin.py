from typing import Dict, List, Optional, cast

from celery import Celery
from fastapi import Depends, Query
from fastapi_jwt_auth import AuthJWT
from lakefs_client.models import CredentialsWithSecret
from sqlmodel import select
from starlette.concurrency import run_in_threadpool

from joj.horse import models, schemas
from joj.horse.models.permission import DefaultRole
from joj.horse.schemas.auth import Authentication, auth_jwt_encode_user
from joj.horse.schemas.base import StandardListResponse, StandardResponse
from joj.horse.services.celery_app import celery_app_dependency
from joj.horse.services.lakefs import ensure_credentials, ensure_user
from joj.horse.utils.errors import ForbiddenError
from joj.horse.utils.fastapi.router import APIRouter
from joj.horse.utils.parser import (
    parse_ordering_query,
    parse_pagination_query,
    parse_uid_detail,
)


def ensure_site_root(auth: Authentication = Depends()) -> None:
    if not auth.is_root():
        raise ForbiddenError(message="site root Permission Denied.")


router = APIRouter(dependencies=[Depends(ensure_site_root)])
router_name = "admin"
router_tag = "admin"


@router.get("/users")
async def admin_list_users(
    ordering: schemas.OrderingQuery = Depends(parse_ordering_query()),
    pagination: schemas.PaginationQuery = Depends(parse_pagination_query),
) -> StandardListResponse[schemas.User]:
    statement = select(models.User)
    users, count = await models.User.execute_list_statement(
        statement, ordering, pagination
    )
    return StandardListResponse(users, count)


@router.get("/domain_roles")
async def admin_list_domain_roles(
    ordering: schemas.OrderingQuery = Depends(parse_ordering_query()),
    pagination: schemas.PaginationQuery = Depends(parse_pagination_query),
) -> StandardListResponse[schemas.DomainRole]:
    statement = select(models.DomainRole)
    domain_roles, count = await models.DomainRole.execute_list_statement(
        statement, ordering, pagination
    )
    return StandardListResponse(domain_roles, count)


@router.get("/judgers")
async def admin_list_judgers(
    celery_app: Celery = Depends(celery_app_dependency),
    ordering: schemas.OrderingQuery = Depends(parse_ordering_query()),
    pagination: schemas.PaginationQuery = Depends(parse_pagination_query),
) -> StandardListResponse[schemas.JudgerDetail]:
    statement = select(models.User).where(models.User.role == DefaultRole.JUDGER)
    users, count = await models.User.execute_list_statement(
        statement, ordering, pagination
    )

    def sync_func() -> Dict[str, Dict[str, str]]:
        worker_names = [f"celery@{cast(models.User, user).username}" for user in users]
        inspect = celery_app.control.inspect(worker_names)
        return inspect.ping()

    ping_res = await run_in_threadpool(sync_func)
    judgers = []
    user: models.User
    for user in users:
        judger = schemas.JudgerDetail(**user.dict(), is_alive=False)
        judger.is_alive = (
            ping_res.get(f"celery@{user.username}", {}).get("ok") == "pong"
        )
        judgers.append(judger)
    return StandardListResponse(judgers, count)


@router.post("/judgers")
async def admin_create_judger(
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


# put endponit including {uid} at last, or it will match wrong part
# to validate UserID, causing 422
@router.get("/{uid}")
async def admin_get_user(
    user: models.User = Depends(parse_uid_detail),
) -> StandardResponse[schemas.UserDetail]:
    return StandardResponse(user)


@router.get("/{uid}/domains")
async def admin_list_user_domains(
    role: Optional[List[str]] = Query(None),
    groups: Optional[List[str]] = Query(None),
    ordering: schemas.OrderingQuery = Depends(parse_ordering_query()),
    pagination: schemas.PaginationQuery = Depends(parse_pagination_query),
    user: models.User = Depends(parse_uid_detail),
) -> StandardListResponse[schemas.Domain]:
    statement = models.Domain.find_by_user_id_statement(user.id, role, groups)
    domains, count = await models.Domain.execute_list_statement(
        statement, ordering, pagination
    )
    return StandardListResponse(domains, count)
