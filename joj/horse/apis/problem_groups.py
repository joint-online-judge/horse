from fastapi import Depends
from sqlmodel import select

from joj.horse import models, schemas
from joj.horse.schemas import StandardListResponse
from joj.horse.schemas.auth import Authentication
from joj.horse.utils.fastapi.router import MyRouter
from joj.horse.utils.parser import parse_ordering_query, parse_pagination_query

router = MyRouter()
router_name = "problem_groups"
router_tag = "problem group"


@router.get("")
async def list_problem_groups(
    ordering: schemas.OrderingQuery = Depends(parse_ordering_query()),
    pagination: schemas.PaginationQuery = Depends(parse_pagination_query),
    auth: Authentication = Depends(),
) -> StandardListResponse[schemas.ProblemGroup]:
    statement = select(models.ProblemGroup)
    problem_groups, count = await models.ProblemGroup.execute_list_statement(
        statement, ordering, pagination
    )
    return StandardListResponse(problem_groups, count)
