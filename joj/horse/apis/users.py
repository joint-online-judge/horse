from typing import List

from fastapi import Depends, Query

from joj.horse import models, schemas
from joj.horse.schemas import StandardListResponse, StandardResponse
from joj.horse.utils.parser import parse_pagination_query, parse_uid
from joj.horse.utils.router import MyRouter

router = MyRouter()
router_name = "users"
router_tag = "user"
router_prefix = "/api/v1"


@router.get("/{uid}")
async def get_user(
    user: models.User = Depends(parse_uid),
) -> StandardResponse[models.UserBase]:
    return StandardResponse(user)


@router.get("/{uid}/domains")
async def get_user_domains(
    user: models.User = Depends(parse_uid),
    role: List[str] = Query([]),
    query: schemas.PaginationQuery = Depends(parse_pagination_query),
) -> StandardListResponse[models.DomainUser]:
    cursor = models.DomainUser.cursor_find_user_domains(user.id, role, query)
    results = await models.DomainUser.to_list(cursor)
    return StandardListResponse(results)


@router.get("/{uid}/problems")
async def get_user_problems(
    user: models.User = Depends(parse_uid),
    query: schemas.PaginationQuery = Depends(parse_pagination_query),
) -> StandardListResponse[models.Problem]:
    condition = {"owner": user.id}
    cursor = models.Problem.cursor_find(condition, query)
    res = await models.Problem.to_list(cursor)
    return StandardListResponse(res)
