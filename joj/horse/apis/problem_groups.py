from fastapi import Depends

from joj.horse import models, schemas
from joj.horse.schemas import StandardListResponse
from joj.horse.utils.auth import Authentication
from joj.horse.utils.parser import parse_pagination_query
from joj.horse.utils.router import MyRouter

router = MyRouter()
router_name = "problem_groups"
router_tag = "problem group"
router_prefix = "/api/v1"


@router.get("")
async def list_problem_groups(
    query: schemas.PaginationQuery = Depends(parse_pagination_query),
    auth: Authentication = Depends(),
) -> StandardListResponse[schemas.ProblemGroup]:
    cursor = models.ProblemGroup.cursor_find({}, query)
    res = await models.ProblemGroup.to_list(cursor)
    return StandardListResponse(res)
