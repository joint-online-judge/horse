from fastapi import Depends

from joj.horse import models, schemas
from joj.horse.schemas import StandardResponse
from joj.horse.schemas.problem import ListProblems
from joj.horse.schemas.problem_group import ListProblemGroups
from joj.horse.utils.auth import Authentication
from joj.horse.utils.parser import parse_problem_group
from joj.horse.utils.router import MyRouter

router = MyRouter()
router_name = "problem_groups"
router_tag = "problem group"
router_prefix = "/api/v1"


@router.get("")
async def list_problem_groups(
    auth: Authentication = Depends(),
) -> StandardResponse[ListProblemGroups]:
    return StandardResponse(
        ListProblemGroups(
            rows=[
                schemas.ProblemGroup.from_orm(problem)
                async for problem in models.ProblemGroup.find({})
            ]
        )
    )


@router.get("/{problem_group}")
async def get_problems_in_problem_group(
    problem_group: models.ProblemGroup = Depends(parse_problem_group),
    auth: Authentication = Depends(),
) -> StandardResponse[ListProblems]:
    return StandardResponse(
        ListProblems(
            rows=[
                schemas.Problem.from_orm(problem)
                async for problem in models.Problem.find({"group": problem_group.id})
            ]
        )
    )
