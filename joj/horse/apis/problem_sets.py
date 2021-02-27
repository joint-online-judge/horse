from typing import List, Optional

from fastapi import Depends, Query
from fastapi_utils.inferring_router import InferringRouter
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.utils import errors
from joj.horse.utils.auth import Authentication
from joj.horse.utils.db import instance
from joj.horse.utils.parser import parse_problem_set

router = InferringRouter()
router_name = "problem_sets"
router_tag = "problem set"
router_prefix = "/api/v1"


@router.get("/{problem_set}", response_model=schemas.ProblemSet)
async def get_problem_set(
    problem_set: models.ProblemSet = Depends(parse_problem_set)
) -> schemas.ProblemSet:
    return schemas.ProblemSet.from_orm(problem_set)


@router.delete("/{problem_set}", status_code=204)
async def delete_problem_set(
    problem_set: models.ProblemSet = Depends(parse_problem_set)
):
    await problem_set.delete()
