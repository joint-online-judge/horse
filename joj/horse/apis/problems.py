from http import HTTPStatus
from typing import Callable, List, NoReturn

from fastapi import APIRouter, Body, Depends, File, Query, Response, UploadFile
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.utils.auth import Authentication
from joj.horse.utils.db import get_db, instance
from joj.horse.utils.errors import (
    DeleteProblemBadRequestError,
    InvalidAuthenticationError,
    ProblemNotFoundError,
)
from joj.horse.utils.parser import parse_problem, parse_problem_set, parse_uid

router = APIRouter()
router_name = "problems"
router_tag = "problem"
router_prefix = "/api/v1"


@router.get("", response_model=List[schemas.Problem])
async def list_problems(
    auth: Authentication = Depends(Authentication),
) -> List[schemas.Problem]:
    return [
        schemas.Problem.from_orm(problem)
        async for problem in models.Problem.find({"owner": auth.user.id})
    ]


@router.post("", response_model=schemas.Problem)
async def create_problem(
    problem: schemas.Problem,
    domain: str = Query(..., description="url or the id of the domain"),
    # title: str = Query(..., description="title of the problem"),
    # content: str = Query("", description="content of the problem"),
    # hidden: bool = Query(False, description="whether the problem is hidden"),
    # languages: List[str] = Query([], description="acceptable language of the problem"),
    auth: Authentication = Depends(),
) -> schemas.Problem:
    if auth.user is None:
        raise InvalidAuthenticationError()

    # use transaction for multiple operations
    try:
        async with instance.session() as session:
            async with session.start_transaction():
                problem_group = schemas.ProblemGroup()
                problem_group = models.ProblemGroup(**problem_group.to_model())
                await problem_group.commit()
                domain = await models.Domain.find_by_url_or_id(domain)
                new_problem = schemas.Problem(
                    title=problem.title,
                    content=problem.content,
                    hidden=problem.hidden,
                    languages=problem.languages,
                    domain=domain.id,
                    owner=auth.user.id,
                    group=problem_group.id,
                )
                new_problem = models.Problem(**new_problem.to_model())
                await new_problem.commit()
                logger.info("problem created: %s", new_problem)

    except Exception as e:
        logger.error("problem creation failed: %s", problem.title)
        raise e
    return schemas.Problem.from_orm(new_problem)


@router.get("/{problem}", response_model=schemas.Problem)
async def get_problem(
    problem: models.Problem = Depends(parse_problem),
) -> schemas.Problem:
    return schemas.Problem.from_orm(problem)


@router.delete("/{problem}", status_code=HTTPStatus.NO_CONTENT, response_class=Response)
async def delete_problem(problem: models.Problem = Depends(parse_problem)) -> None:
    # TODO: optimize
    async for problem_set in models.ProblemSet.find():
        if problem in problem_set:
            raise DeleteProblemBadRequestError
    await problem.delete()


@router.patch("/{problem}", response_model=schemas.Problem)
async def update_problem(
    edit_problem: schemas.EditProblem, problem: models.Problem = Depends(parse_problem)
) -> schemas.Problem:
    problem.update_from_schema(edit_problem)
    await problem.commit()
    return schemas.Problem.from_orm(problem)


@router.post("/{problem}/clone", response_model=schemas.Problem)
async def clone_problem(
    problem: models.Problem = Depends(parse_problem),
    domain: str = Query(..., description="url or the id of the domain"),
    new_group: bool = Query(
        False, description="create new problem group or use the original one"
    ),
    auth: Authentication = Depends(),
) -> schemas.Problem:
    # use transaction for multiple operations
    try:
        async with instance.session() as session:
            async with session.start_transaction():
                domain = await models.Domain.find_by_url_or_id(domain)
                if new_group:
                    problem_group = schemas.ProblemGroup()
                    problem_group = models.ProblemGroup(**problem_group.to_model())
                    await problem_group.commit()
                else:
                    problem_group = await problem.group.fetch()
                new_problem = schemas.Problem(
                    title=problem.title,
                    content=problem.content,
                    hidden=problem.hidden,
                    languages=problem.languages,
                    domain=domain.id,
                    owner=auth.user.id,
                    group=problem_group.id,  # type: ignore
                )
                new_problem = models.Problem(**new_problem.to_model())
                await new_problem.commit()
                logger.info("problem created: %s", new_problem)

    except Exception as e:
        logger.error("problem clone failed: %s", problem.title)
        raise e
    return schemas.Problem.from_orm(new_problem)


@router.post("/{problem_set}/{problem}", response_model=schemas.Record)
async def submit_solution_to_problem(
    code_type: schemas.RecordCodeType = Body(...),
    file: UploadFile = File(...),
    problem_set: models.ProblemSet = Depends(parse_problem_set),
    problem: models.Problem = Depends(parse_problem),
    auth: Authentication = Depends(),
) -> schemas.Record:
    try:
        gfs = AsyncIOMotorGridFSBucket(get_db())
        file_id = await gfs.upload_from_stream(
            filename=file.filename,
            source=await file.read(),
            metadata={"contentType": file.content_type, "compressed": True},
        )
        record = schemas.Record(
            domain=problem.domain,
            problem=problem.id,
            problem_set=problem_set.id,
            user=auth.user.id,
            code_type=code_type,
            code=file_id,
            judge_category=[],
        )
        record = models.Record(**record.to_model())
        await record.commit()
        logger.info("problem submitted with record: %s", record.id)

    except Exception as e:
        logger.error("problem submission failed: %s", problem.id)
        raise e

    return schemas.Record.from_orm(record)


@router.delete(
    "/{problem_set}/{problem}",
    status_code=HTTPStatus.NO_CONTENT,
    response_class=Response,
)
async def delete_problem_from_problem_set(
    problem_set: models.ProblemSet = Depends(parse_problem_set),
    problem: models.Problem = Depends(parse_problem),
    auth: Authentication = Depends(),
) -> None:
    if problem not in problem_set.problems:
        raise ProblemNotFoundError(problem.id)
    problem_set.problems.remove(problem)
    await problem_set.commit()


@router.put("/{problem_set}/{problem}", response_model=schemas.ProblemSet)
async def add_problem_to_problem_set(
    problem_set: models.ProblemSet = Depends(parse_problem_set),
    problem: models.Problem = Depends(parse_problem),
    auth: Authentication = Depends(),
) -> schemas.ProblemSet:
    if problem not in problem_set.problems:
        problem_set.problems.append(problem)
        await problem_set.commit()
    return schemas.ProblemSet.from_orm(problem_set)
