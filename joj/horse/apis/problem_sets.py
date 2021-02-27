from http import HTTPStatus
from typing import List, Optional

from fastapi import Depends, Query
from fastapi_utils.inferring_router import InferringRouter
from starlette.responses import Response
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.utils.auth import Authentication
from joj.horse.utils.db import instance
from joj.horse.utils.errors import InvalidAuthenticationError
from joj.horse.utils.parser import parse_problem_set

router = InferringRouter()
router_name = "problem_sets"
router_tag = "problem set"
router_prefix = "/api/v1"


@router.get("", response_model=List[schemas.ProblemSet])
async def list_problem_sets(
    auth: Authentication = Depends(Authentication),
) -> List[schemas.ProblemSet]:
    return [
        schemas.ProblemSet.from_orm(problem_set)
        async for problem_set in models.ProblemSet.find({"owner": auth.user.id})
    ]


@router.post("", response_model=schemas.ProblemSet)
async def create_problem_set(
    domain: str = Query(..., description="url or the id of the domain"),
    title: str = Query(..., description="title of the problem set"),
    content: str = Query("", description="content of the problem set"),
    hidden: bool = Query(False, description="whether the problem set is hidden"),
    problems: List[str] = Query(
        [], description="problems belonging to the problem set"
    ),
    auth: Authentication = Depends(),
) -> schemas.ProblemSet:
    if auth.user is None:
        raise InvalidAuthenticationError()

    # use transaction for multiple operations
    try:
        async with instance.session() as session:
            async with session.start_transaction():
                domain = await models.Domain.find_by_url_or_id(domain)
                problems_models = [
                    await models.Problem.find_by_id(problem) for problem in problems
                ]
                problems_models = [problem.id for problem in problems_models]
                logger.info("problems_models: %s", problems_models)
                problem_set = schemas.ProblemSet(
                    title=title,
                    content=content,
                    hidden=hidden,
                    domain=domain.id,
                    owner=auth.user.id,
                    problems=problems_models,
                )
                problem_set = models.ProblemSet(**problem_set.to_model())
                await problem_set.commit()
                logger.info("problem set created: %s", problem_set)

    except Exception as e:
        logger.error("problem set creation failed: %s", title)
        raise e
    return schemas.ProblemSet.from_orm(problem_set)


@router.get("/{problem_set}", response_model=schemas.ProblemSet)
async def get_problem_set(
    problem_set: models.ProblemSet = Depends(parse_problem_set),
) -> schemas.ProblemSet:
    return schemas.ProblemSet.from_orm(problem_set)


@router.delete("/{problem_set}", status_code=HTTPStatus.NO_CONTENT)
async def delete_problem_set(
    problem_set: models.ProblemSet = Depends(parse_problem_set),
):
    await problem_set.delete()
    return Response(status_code=HTTPStatus.NO_CONTENT.value)
