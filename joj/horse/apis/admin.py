from fastapi import Depends
from sqlmodel import select

from joj.horse import models, schemas
from joj.horse.models.permission import DefaultRole
from joj.horse.schemas.base import StandardListResponse
from joj.horse.utils.auth import Authentication
from joj.horse.utils.errors import ForbiddenError
from joj.horse.utils.parser import parse_ordering_query, parse_pagination_query
from joj.horse.utils.router import MyRouter


def ensure_site_root(auth: Authentication = Depends()) -> None:
    if not auth.is_root():
        raise ForbiddenError(message="site root Permission Denied.")


router = MyRouter(dependencies=[Depends(ensure_site_root)])
router_name = "admin"
router_tag = "admin"
router_prefix = "/api/v1"


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


# @router.post("/users")
# async def create_user(
#     student_id: str,
#     jaccount_name: str,
#     real_name: str,
#     ip: str,
#     auth: Authentication = Depends(),
# ) -> StandardResponse[schemas.User]:
#     user = await models.User.login_by_jaccount(
#         student_id=student_id, jaccount_name=jaccount_name, real_name=real_name, ip=ip
#     )
#     assert user is not None
#     return StandardResponse(models.User.from_orm(user))


# @router.delete("/users/{uid}")
# async def delete_user(
#     user: models.User = Depends(parse_uid), auth: Authentication = Depends()
# ) -> StandardResponse[Empty]:
#     await user.delete_model()
#     return StandardResponse()


# @router.get("/domain_users")
# async def list_domain_users(
#     pagination: schemas.PaginationQuery = Depends(parse_pagination_query),
#     auth: Authentication = Depends(),
# ) -> StandardListResponse[models.DomainUser]:
#     cursor = models.DomainUser.cursor_find({}, query)
#     res = await models.DomainUser.to_list(cursor)
#     return StandardListResponse(res)


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
    statement = select(models.User).where(models.User.role == DefaultRole.JUDGE)
    users, count = await models.User.execute_list_statement(
        statement, ordering, pagination
    )
    return StandardListResponse(users, count)


# @router.post("/judgers")
# async def create_judger(
#     uname: str, mail: EmailStr, auth: Authentication = Depends()
# ) -> StandardResponse[schemas.User]:
#     # TODO: scope
#     user_schema = models.User(
#         scope="sjtu",
#         role=DefaultRole.JUDGE,
#         uname=uname,
#         mail=mail,
#         register_timestamp=datetime.utcnow(),
#         login_timestamp=datetime.utcnow(),
#     )
#     user = models.User(**user_schema.to_model())
#     await user.commit()
#     return StandardResponse(models.User.from_orm(user))
