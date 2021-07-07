from datetime import datetime
from typing import List, Optional

from bson.objectid import ObjectId
from fastapi import Body, Depends, File, Form, Query, UploadFile
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.apis import records
from joj.horse.models.permission import Permission
from joj.horse.schemas import Empty, StandardResponse
from joj.horse.schemas.base import PydanticObjectId
from joj.horse.schemas.problem import ListProblems
from joj.horse.tasks import celery_app
from joj.horse.utils.auth import Authentication, ensure_permission
from joj.horse.utils.db import get_db, instance
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.parser import (
    parse_domain,
    parse_problem,
    parse_problem_set,
    parse_problem_set_body,
    parse_problems,
    parse_query,
    parse_user_from_auth,
)
from joj.horse.utils.router import MyRouter
from joj.horse.utils.url import generate_url

router = MyRouter()
router_name = "domains/{domain}/problems"
router_tag = "problem"
router_prefix = "/api/v1"


@router.get(
    "", dependencies=[Depends(ensure_permission(Permission.DomainProblem.view))]
)
async def list_problems(
    domain: models.Domain = Depends(parse_domain),
    problem_set: Optional[PydanticObjectId] = Query(None),
    problem_group: Optional[PydanticObjectId] = Query(None),
    query: schemas.BaseQuery = Depends(parse_query),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[ListProblems]:
    condition = {"owner": user.id}
    if domain is not None:
        condition["domain"] = domain.id
    if problem_set is not None:
        condition["problem_set"] = ObjectId(problem_set)
    if problem_group is not None:
        condition["problem_group"] = ObjectId(problem_group)
    cursor = models.Problem.cursor_find(condition, query)
    res = await schemas.Problem.to_list(cursor)
    return StandardResponse(ListProblems(results=res))


@router.post(
    "", dependencies=[Depends(ensure_permission(Permission.DomainProblem.create))]
)
async def create_problem(
    problem: schemas.ProblemCreate,
    domain: models.Domain = Depends(parse_domain),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[schemas.Problem]:
    # problem_set: models.ProblemSet = await models.ProblemSet.find_by_id(
    #     problem.problem_set
    # )
    try:
        async with instance.session() as session:
            async with session.start_transaction():
                problem_group = schemas.ProblemGroup()
                problem_group = models.ProblemGroup(**problem_group.to_model())
                await problem_group.commit()
                problem_model = schemas.Problem(
                    domain=domain.id,
                    title=problem.title,
                    content=problem.content,
                    # data_version=problem.data_version,
                    # languages=problem.languages,
                    # problem_set=problem_set.id,
                    owner=user.id,
                    problem_group=problem_group.id,
                )
                problem_model = models.Problem(**problem_model.to_model())
                await problem_model.commit()
                logger.info("problem created: %s", problem_model)
    except Exception as e:
        logger.error("problem creation failed: %s", problem.title)
        raise e
    return StandardResponse(schemas.Problem.from_orm(problem_model))


@router.get(
    "/{problem}",
    dependencies=[Depends(ensure_permission(Permission.DomainProblem.view))],
)
async def get_problem(
    problem: models.Problem = Depends(parse_problem),
) -> StandardResponse[schemas.Problem]:
    return StandardResponse(schemas.Problem.from_orm(problem))


@router.delete(
    "/{problem}",
    dependencies=[Depends(ensure_permission(Permission.DomainProblem.edit))],
)
async def delete_problem(
    problem: models.Problem = Depends(parse_problem),
) -> StandardResponse[Empty]:
    await problem.delete()
    return StandardResponse()


@router.patch(
    "/{problem}",
    dependencies=[Depends(ensure_permission(Permission.DomainProblem.edit))],
)
async def update_problem(
    edit_problem: schemas.ProblemEdit, problem: models.Problem = Depends(parse_problem)
) -> StandardResponse[schemas.Problem]:
    problem.update_from_schema(edit_problem)
    await problem.commit()
    return StandardResponse(schemas.Problem.from_orm(problem))


@router.patch(
    "/{problem}/config",
    dependencies=[Depends(ensure_permission(Permission.DomainProblem.view_config))],
)
async def update_problem_config(
    config: UploadFile = File(...), problem: models.Problem = Depends(parse_problem)
) -> StandardResponse[schemas.Problem]:
    return StandardResponse(schemas.Problem.from_orm(problem))


@router.post(
    "/clone",
    dependencies=[Depends(ensure_permission(Permission.DomainProblem.view_config))],
)
async def clone_problem(
    problems: List[models.Problem] = Depends(parse_problems),
    problem_set: models.ProblemSet = Depends(parse_problem_set_body),
    new_group: bool = Body(False, description="whether to create new problem group"),
    domain: models.Domain = Depends(parse_domain),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[ListProblems]:
    try:
        async with instance.session() as session:
            async with session.start_transaction():
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
                        owner=user.id,
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


@router.post(
    "/{problem}",
    dependencies=[Depends(ensure_permission(Permission.DomainProblem.submit))],
)
async def submit_solution_to_problem(
    code_type: schemas.RecordCodeType = Form(...),
    file: UploadFile = File(...),
    problem: models.Problem = Depends(parse_problem),
    domain: models.Domain = Depends(parse_domain),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[schemas.Record]:
    if domain.id != problem.domain:
        # TODO: test whether problem.domain is object id and add other error code
        raise BizError(ErrorCode.ProblemNotFoundError)
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
            user=user.id,
            code_type=code_type,
            code=file_id,
            judge_category=[],
            submit_at=datetime.utcnow(),
            cases=[schemas.RecordCase() for i in range(10)],  # TODO: modify later
        )
        record_model = models.Record(**record.to_model())
        await record_model.commit()
        problem.num_submit += 1
        await problem.commit()
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
