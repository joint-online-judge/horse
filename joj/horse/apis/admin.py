from fastapi import Depends
from fastapi_jwt_auth import AuthJWT
from sqlmodel import select

from joj.horse import models, schemas
from joj.horse.models.permission import DefaultRole
from joj.horse.schemas.auth import Authentication, auth_jwt_encode_user
from joj.horse.schemas.base import StandardListResponse
from joj.horse.utils.errors import ForbiddenError
from joj.horse.utils.fastapi.router import MyRouter
from joj.horse.utils.parser import parse_ordering_query, parse_pagination_query


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
) -> schemas.StandardResponse[schemas.AuthTokens]:
    user_model = await models.User.create_judger(judger_create)
    access_token, refresh_token = auth_jwt_encode_user(auth_jwt, user=user_model)
    return schemas.StandardResponse(
        schemas.AuthTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )
    )
