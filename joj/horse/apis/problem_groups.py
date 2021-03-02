from http import HTTPStatus
from typing import List

from fastapi import Depends, Query
from fastapi_utils.inferring_router import InferringRouter
from starlette.responses import Response
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.utils.auth import Authentication
from joj.horse.utils.db import instance
from joj.horse.utils.errors import (
    DeleteProblemBadRequestError,
    InvalidAuthenticationError,
    ProblemNotFoundError,
)
from joj.horse.utils.parser import (
    parse_problem,
    parse_problem_group,
    parse_problem_set,
    parse_uid,
)

router = InferringRouter()
router_name = "problem_groups"
router_tag = "problem group"
router_prefix = "/api/v1"


@router.get("", response_model=List[schemas.ProblemGroup])
async def list_problem_groups(
    auth: Authentication = Depends(Authentication),
) -> List[schemas.ProblemGroup]:
    return [
        schemas.ProblemGroup.from_orm(problem)
        async for problem in models.ProblemGroup.find({})
    ]


@router.get("/{problem_group}", response_model=List[schemas.Problem])
async def get_problems_in_problem_group(
    problem_group: models.ProblemGroup = Depends(parse_problem_group),
) -> List[schemas.Problem]:
    return [
        schemas.Problem.from_orm(problem)
        async for problem in models.Problem.find({"group": problem_group.id})
    ]
