from fastapi import Depends

from joj.horse import models, schemas
from joj.horse.schemas import StandardResponse
from joj.horse.schemas.problem import ListProblems
from joj.horse.schemas.problem_group import ListProblemGroups
from joj.horse.utils.auth import Authentication
from joj.horse.utils.parser import parse_problem_group, parse_query
from joj.horse.utils.router import MyRouter

router = MyRouter()
router_name = "problem_groups"
router_tag = "problem group"
router_prefix = "/api/v1"


@router.get("")
async def list_problem_groups(
    query: schemas.BaseFilter = Depends(parse_query), auth: Authentication = Depends()
) -> StandardResponse[ListProblemGroups]:
    res = await schemas.ProblemGroup.to_list({}, query)
    return StandardResponse(ListProblemGroups(results=res))
