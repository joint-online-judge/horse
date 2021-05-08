from datetime import datetime

from fastapi import Body, Depends, File, Query, UploadFile
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.schemas import Empty, StandardResponse
from joj.horse.schemas.problem import ListProblems
from joj.horse.utils.auth import Authentication
from joj.horse.utils.db import get_db, instance
from joj.horse.utils.errors import BizError, ErrorEnum
from joj.horse.utils.parser import parse_problem, parse_problem_set
from joj.horse.utils.router import MyRouter

router = MyRouter()
router_name = "problems"
router_tag = "problem"
router_prefix = "/api/v1"


@router.get("")
async def list_problems(
    auth: Authentication = Depends(),
) -> StandardResponse[ListProblems]:
    return StandardResponse(
        ListProblems(
            rows=[
                schemas.Problem.from_orm(problem)
                async for problem in models.Problem.find({"owner": auth.user.id})
            ]
        )
    )


@router.post("")
async def create_problem(
    problem: schemas.ProblemCreate, auth: Authentication = Depends()
) -> StandardResponse[schemas.Problem]:
    if auth.user is None:
        raise BizError(ErrorEnum.InvalidAuthenticationError)
    domain = await models.Domain.find_by_url_or_id(problem.domain)

    # use transaction for multiple operations
    try:
        async with instance.session() as session:
            async with session.start_transaction():
                problem_group = schemas.ProblemGroup()
                problem_group = models.ProblemGroup(**problem_group.to_model())
                await problem_group.commit()
                # domain = await models.Domain.find_by_id(problem.domain.__str__())
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
    return StandardResponse(schemas.Problem.from_orm(new_problem))


@router.get("/{problem}")
async def get_problem(
    problem: models.Problem = Depends(parse_problem),
) -> StandardResponse[schemas.Problem]:
    return StandardResponse(schemas.Problem.from_orm(problem))


@router.delete("/{problem}")
async def delete_problem(
    problem: models.Problem = Depends(parse_problem),
) -> StandardResponse[Empty]:
    # TODO: optimize
    async for problem_set in models.ProblemSet.find():
        if problem in problem_set:
            raise BizError(ErrorEnum.DeleteProblemBadRequestError)
    await problem.delete()
    return StandardResponse()


@router.patch("/{problem}")
async def update_problem(
    edit_problem: schemas.ProblemEdit, problem: models.Problem = Depends(parse_problem)
) -> StandardResponse[schemas.Problem]:
    problem.update_from_schema(edit_problem)
    await problem.commit()
    return StandardResponse(schemas.Problem.from_orm(problem))


@router.post("/{problem}/clone")
async def clone_problem(
    problem: models.Problem = Depends(parse_problem),
    domain: str = Query(..., description="url or the id of the domain"),
    new_group: bool = Query(
        False, description="create new problem group or use the original one"
    ),
    auth: Authentication = Depends(),
) -> StandardResponse[schemas.Problem]:
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
    return StandardResponse(schemas.Problem.from_orm(new_problem))


@router.post("/{problem_set}/{problem}")
async def submit_solution_to_problem(
    code_type: schemas.RecordCodeType = Body(...),
    file: UploadFile = File(...),
    problem_set: models.ProblemSet = Depends(parse_problem_set),
    problem: models.Problem = Depends(parse_problem),
    auth: Authentication = Depends(),
) -> StandardResponse[schemas.Record]:
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
            submit_at=datetime.utcnow(),
            judge_at=datetime.utcnow(),  # TODO: modify later
            judge_user=auth.user.id,  # TODO: modify later
        )
        record = models.Record(**record.to_model())
        await record.commit()
        logger.info("problem submitted with record: %s", record.id)

    except Exception as e:
        logger.error("problem submission failed: %s", problem.id)
        raise e

    return StandardResponse(schemas.Record.from_orm(record))


@router.delete("/{problem_set}/{problem}")
async def delete_problem_from_problem_set(
    problem_set: models.ProblemSet = Depends(parse_problem_set),
    problem: models.Problem = Depends(parse_problem),
    auth: Authentication = Depends(),
) -> StandardResponse[Empty]:
    if problem not in problem_set.problems:
        raise BizError(ErrorEnum.ProblemNotFoundError)
    problem_set.problems.remove(problem)
    await problem_set.commit()
    return StandardResponse()


@router.put("/{problem_set}/{problem}")
async def add_problem_to_problem_set(
    problem_set: models.ProblemSet = Depends(parse_problem_set),
    problem: models.Problem = Depends(parse_problem),
    auth: Authentication = Depends(),
) -> StandardResponse[schemas.ProblemSet]:
    if problem not in problem_set.problems:
        problem_set.problems.append(problem)
        await problem_set.commit()
    return StandardResponse(schemas.ProblemSet.from_orm(problem_set))
