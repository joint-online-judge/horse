from http import HTTPStatus
from typing import List

from fastapi import APIRouter, Depends, Query, Response
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.utils.auth import Authentication
from joj.horse.utils.db import instance
from joj.horse.utils.errors import InvalidAuthenticationError, ProblemNotFoundError
from joj.horse.utils.parser import parse_problem_set

router = APIRouter()
router_name = "problem_sets"
router_tag = "problem set"
router_prefix = "/api/v1"


@router.get("", response_model=List[schemas.ProblemSet])
async def list_problem_sets(
    required_labels: List[str] = Query([]), auth: Authentication = Depends()
) -> List[schemas.ProblemSet]:
    return [
        schemas.ProblemSet.from_orm(problem_set)
        async for problem_set in models.ProblemSet.find({"owner": auth.user.id})
        if all(label in problem_set.labels for label in required_labels)
    ]


@router.post("", response_model=schemas.ProblemSet)
async def create_problem_set(
    problem_set: schemas.ProblemSetCreate, auth: Authentication = Depends()
) -> schemas.ProblemSet:
    if auth.user is None:
        raise InvalidAuthenticationError()

    # use transaction for multiple operations
    try:
        async with instance.session() as session:
            async with session.start_transaction():
                domain = await models.Domain.find_by_url_or_id(problem_set.domain)
                problems_models = [
                    await models.Problem.find_by_id(problem)
                    for problem in problem_set.problems
                ]
                for i, (problem_id, problem_model) in enumerate(
                    zip(problem_set.problems, problems_models)
                ):
                    if problem_model is None:
                        raise ProblemNotFoundError(problem_id)
                    problems_models[i] = problem_model.id
                logger.info("problems_models: %s", problems_models)
                problem_set = schemas.ProblemSet(
                    title=problem_set.title,
                    content=problem_set.content,
                    hidden=problem_set.hidden,
                    domain=domain.id,
                    owner=auth.user.id,
                    problems=problems_models,
                )
                problem_set = models.ProblemSet(**problem_set.to_model())
                await problem_set.commit()
                logger.info("problem set created: %s", problem_set)

    except Exception as e:
        logger.error("problem set creation failed: %s", problem_set.title)
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
) -> None:
    await problem_set.delete()


@router.patch("/{problem_set}", response_model=schemas.ProblemSet)
async def update_problem_set(
    edit_problem_set: schemas.ProblemSetEdit,
    problem_set: models.ProblemSet = Depends(parse_problem_set),
) -> schemas.ProblemSet:
    problem_set.update_from_schema(edit_problem_set)
    await problem_set.commit()
    return schemas.ProblemSet.from_orm(problem_set)
