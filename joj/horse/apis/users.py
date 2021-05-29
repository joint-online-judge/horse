from typing import List

from fastapi import Depends, Query

from joj.horse import models, schemas
from joj.horse.schemas import StandardResponse
from joj.horse.schemas.domain_user import ListDomainMembers
from joj.horse.schemas.problem import ListProblems
from joj.horse.utils.auth import Authentication
from joj.horse.utils.parser import parse_query, parse_uid
from joj.horse.utils.router import MyRouter

router = MyRouter()
router_name = "users"
router_tag = "user"
router_prefix = "/api/v1"


@router.get("/{uid}")
async def get_user(
    user: models.User = Depends(parse_uid), auth: Authentication = Depends()
) -> StandardResponse[schemas.UserBase]:
    return StandardResponse(schemas.UserBase.from_orm(user))


@router.get("/{uid}/domains")
async def get_user_domains(
    user: models.User = Depends(parse_uid),
    role: List[str] = Query([]),
    query: schemas.BaseQuery = Depends(parse_query),
) -> StandardResponse[ListDomainMembers]:
    cursor = models.DomainUser.cursor_find_user_domains(user.id, role, query)
    results = await schemas.DomainUser.to_list(cursor)
    return StandardResponse(ListDomainMembers(results=results))


@router.get("/{uid}/problems")
async def get_user_problems(
    user: models.User = Depends(parse_uid),
    query: schemas.BaseQuery = Depends(parse_query),
) -> StandardResponse[ListProblems]:
    condition = {"owner": user.id}
    cursor = models.Problem.cursor_find(condition, query)
    res = await schemas.Problem.to_list(cursor)
    return StandardResponse(ListProblems(results=res))
