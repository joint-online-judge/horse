from datetime import datetime
from typing import List, Optional

from bson.objectid import ObjectId
from fastapi import Body, Depends, File, Form, Query, UploadFile
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.apis import records
from joj.horse.schemas import Empty, StandardResponse
from joj.horse.schemas.base import PydanticObjectId
from joj.horse.schemas.problem import ListProblems
from joj.horse.tasks import celery_app
from joj.horse.utils.auth import Authentication
from joj.horse.utils.db import get_db, instance
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.parser import (
    parse_problem,
    parse_problem_set,
    parse_problem_set_body,
    parse_problems,
    parse_query,
)
from joj.horse.utils.router import MyRouter
from joj.horse.utils.url import generate_url

router = MyRouter()
router_name = "problems"
router_tag = "problem"
router_prefix = "/api/v1"


@router.get("")
async def list_problems(
    domain: Optional[PydanticObjectId] = Query(None),
    problem_set: Optional[PydanticObjectId] = Query(None),
    problem_group: Optional[PydanticObjectId] = Query(None),
    query: schemas.BaseQuery = Depends(parse_query),
    auth: Authentication = Depends(),
) -> StandardResponse[ListProblems]:
    filter = {"owner": auth.user.id}
    if domain is not None:
        filter["domain"] = ObjectId(domain)
    if problem_set is not None:
        filter["problem_set"] = ObjectId(problem_set)
    if problem_group is not None:
        filter["problem_group"] = ObjectId(problem_group)
    res = await schemas.Problem.to_list(filter, query)
    return StandardResponse(ListProblems(results=res))


@router.post("")
async def create_problem(
    problem: schemas.ProblemCreate, auth: Authentication = Depends()
) -> StandardResponse[schemas.Problem]:
    problem_set: models.ProblemSet = await models.ProblemSet.find_by_id(
        problem.problem_set
    )
    domain: models.Domain = await problem_set.domain.fetch()
    try:
        async with instance.session() as session:
            async with session.start_transaction():
                problem_group = schemas.ProblemGroup()
                problem_group = models.ProblemGroup(**problem_group.to_model())
                await problem_group.commit()
                new_problem = schemas.Problem(
                    domain=domain.id,
                    title=problem.title,
                    content=problem.content,
                    data_version=problem.data_version,
                    languages=problem.languages,
                    problem_set=problem_set.id,
                    owner=auth.user.id,
                    problem_group=problem_group.id,
                )
                new_problem = models.Problem(**new_problem.to_model())
                await new_problem.commit()
                problem_set.update({})  # TODO: add new problem to problem_set
                await problem_set.commit()
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
    await problem.delete()
    return StandardResponse()


@router.patch("/{problem}")
async def update_problem(
    edit_problem: schemas.ProblemEdit, problem: models.Problem = Depends(parse_problem)
) -> StandardResponse[schemas.Problem]:
    problem.update_from_schema(edit_problem)
    await problem.commit()
    return StandardResponse(schemas.Problem.from_orm(problem))


@router.post("/clone")
async def clone_problem(
    problems: List[models.Problem] = Depends(parse_problems),
    problem_set: models.ProblemSet = Depends(parse_problem_set_body),
    new_group: bool = Body(False, description="whether to create new problem group"),
    auth: Authentication = Depends(),
) -> StandardResponse[ListProblems]:
    try:
        async with instance.session() as session:
            async with session.start_transaction():
                domain: models.Domain = await problem_set.domain.fetch()
                res = []
                for problem in problems:
                    if new_group:
                        problem_group = models.ProblemGroup(
                            **schemas.ProblemGroup().to_model()
                        )
                        await problem_group.commit()
                    else:
                        problem_group = await problem.problem_group.fetch()
                    new_problem = schemas.Problem(
                        domain=domain.id,
                        owner=auth.user.id,
                        title=problem.title,
                        content=problem.content,
                        data=problem.data,
                        data_version=problem.data_version,
                        languages=problem.languages,
                        problem_group=problem_group.id,
                        problem_set=problem_set.id,
                    )
                    new_problem = models.Problem(**new_problem.to_model())
                    await new_problem.commit()
                    res.append(schemas.Problem.from_orm(new_problem))
                    logger.info("problem cloned: %s", new_problem)
    except Exception as e:
        logger.error("problems clone to problem set failed: %s", problem_set)
        raise e
    return StandardResponse(ListProblems(results=res))


@router.post("/{problem}")
async def submit_solution_to_problem(
    code_type: schemas.RecordCodeType = Form(...),
    file: UploadFile = File(...),
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
            user=auth.user.id,
            code_type=code_type,
            code=file_id,
            judge_category=[],
            submit_at=datetime.utcnow(),
            cases=[schemas.RecordCase() for i in range(10)],  # TODO: modify later
        )
        record_model = models.Record(**record.to_model())
        await record_model.commit()
        logger.info("problem submitted with record: %s", record_model.id)
    except Exception as e:
        logger.error("problem submission failed: %s", problem.id)
        raise e
    record_schema = schemas.Record.from_orm(record_model)
    http_url = generate_url(
        records.router_prefix, records.router_name, record_schema.id
    )
    celery_app.send_task("joj.tiger.compile", args=[record_schema.dict(), http_url])
    return StandardResponse(record_schema)
