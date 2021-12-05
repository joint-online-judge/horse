from typing import List, Optional

from fastapi import Depends, Query

from joj.horse import models, schemas
from joj.horse.schemas import StandardListResponse, StandardResponse
from joj.horse.schemas.permission import Permission
from joj.horse.utils.parser import (
    parse_ordering_query,
    parse_pagination_query,
    parse_uid,
)
from joj.horse.utils.router import MyRouter

router = MyRouter()
router_name = "users"
router_tag = "user"
router_prefix = "/api/v1"


@router.get("", permissions=[Permission.SiteUser.view_list])
async def list_users(
    ordering: schemas.OrderingQuery = Depends(parse_ordering_query(["username"])),
    pagination: schemas.PaginationQuery = Depends(parse_pagination_query),
    query: str = Query(""),
) -> StandardListResponse[schemas.User]:
    statement = models.User.find_users_statement(query)
    problem_sets, count = await models.User.execute_list_statement(
        statement, ordering, pagination
    )
    return StandardListResponse(problem_sets, count)


@router.get("/{uid}")
async def get_user(
    user: models.User = Depends(parse_uid),
) -> StandardResponse[schemas.User]:
    return StandardResponse(user)


@router.get("/{uid}/domains")
async def list_user_domains(
    role: Optional[List[str]] = Query(None),
    ordering: schemas.OrderingQuery = Depends(parse_ordering_query()),
    pagination: schemas.PaginationQuery = Depends(parse_pagination_query),
    user: models.User = Depends(parse_uid),
) -> StandardListResponse[schemas.Domain]:
    statement = user.find_domains_statement(role)
    domains, count = await models.Domain.execute_list_statement(
        statement, ordering, pagination
    )
    return StandardListResponse(domains, count)


@router.get("/{uid}/problems")
async def get_user_problems(
    user: models.User = Depends(parse_uid),
    query: schemas.PaginationQuery = Depends(parse_pagination_query),
) -> StandardListResponse[schemas.Problem]:
    condition = {"owner": user.id}
    cursor = models.Problem.cursor_find(condition, query)
    res = await models.Problem.to_list(cursor)
    return StandardListResponse(res)
