from datetime import datetime
from typing import Optional

from fastapi import BackgroundTasks, Depends, File, Form, Query, UploadFile
from sqlmodel.ext.asyncio.session import AsyncSession
from tortoise import transactions
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.apis import records
from joj.horse.schemas import Empty, StandardListResponse, StandardResponse
from joj.horse.schemas.base import PydanticObjectId
from joj.horse.schemas.permission import Permission

# from joj.horse.schemas.problem import ListProblems, ProblemClone
from joj.horse.tasks import celery_app
from joj.horse.utils.auth import Authentication, ensure_permission
from joj.horse.utils.db import db_session_dependency
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.lakefs import LakeFSProblemConfig
from joj.horse.utils.parser import (
    parse_domain_from_auth,
    parse_ordering_query,
    parse_pagination_query,
    parse_problem,
    parse_problem_set,
    parse_user_from_auth,
    parse_view_hidden_problem,
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
    domain: models.Domain = Depends(parse_domain_from_auth),
    problem_set: Optional[PydanticObjectId] = Query(None),
    problem_group: Optional[PydanticObjectId] = Query(None),
    ordering: schemas.OrderingQuery = Depends(parse_ordering_query()),
    pagination: schemas.PaginationQuery = Depends(parse_pagination_query),
    include_hidden: bool = Depends(parse_view_hidden_problem),
) -> StandardListResponse[models.Problem]:
    problems, count = await domain.find_problems(
        include_hidden=include_hidden,
        problem_set=problem_set,
        problem_group=problem_group,
        ordering=ordering,
        pagination=pagination,
    )
    problems = [models.Problem.from_orm(problem) for problem in problems]
    return StandardListResponse(problems, count)


@router.post(
    "", dependencies=[Depends(ensure_permission(Permission.DomainProblem.create))]
)
async def create_problem(
    problem_create: models.ProblemCreate,
    background_tasks: BackgroundTasks,
    domain: models.Domain = Depends(parse_domain_from_auth),
    user: models.User = Depends(parse_user_from_auth),
    session: AsyncSession = Depends(db_session_dependency),
) -> StandardResponse[models.Problem]:
    try:
        problem_group = models.ProblemGroup()
        session.sync_session.add(problem_group)
        logger.info("problem group created: %s", problem_group)
        problem = models.Problem(
            **problem_create.dict(),
            domain=domain,
            owner=user,
            problem_group=problem_group,
        )
        session.sync_session.add(problem)
        logger.info("problem created: %s", problem)
        await session.commit()
    except Exception as e:
        logger.exception("problem creation failed: %s", problem_create)
        raise e
    lakefs_problem_config = LakeFSProblemConfig(problem)
    background_tasks.add_task(lakefs_problem_config.ensure_branch)
    return StandardResponse(models.Problem.from_orm(problem))


@router.get(
    "/{problem}",
    dependencies=[Depends(ensure_permission(Permission.DomainProblem.view))],
)
async def get_problem(
    problem: models.Problem = Depends(parse_problem),
) -> StandardResponse[models.Problem]:
    return StandardResponse(problem)


@router.delete(
    "/{problem}",
    dependencies=[Depends(ensure_permission(Permission.DomainProblem.edit))],
)
async def delete_problem(
    problem: models.Problem = Depends(parse_problem),
    session: AsyncSession = Depends(db_session_dependency),
) -> StandardResponse[Empty]:
    await session.delete(problem)
    return StandardResponse()


@router.patch(
    "/{problem}",
    dependencies=[Depends(ensure_permission(Permission.DomainProblem.edit))],
)
async def update_problem(
    edit_problem: models.ProblemEdit,
    problem: models.Problem = Depends(parse_problem),
    session: AsyncSession = Depends(db_session_dependency),
) -> StandardResponse[models.Problem]:
    problem.update_from_schema(edit_problem)
    session.sync_session.add(problem)
    await session.commit()
    return StandardResponse(models.Problem.from_orm(problem))


@router.patch(
    "/{problem}/config",
    dependencies=[Depends(ensure_permission(Permission.DomainProblem.view_config))],
)
async def update_problem_config(
    config: UploadFile = File(...), problem: models.Problem = Depends(parse_problem)
) -> StandardResponse[models.Problem]:
    return StandardResponse(models.Problem.from_orm(problem))


@router.post(
    "/clone",
    dependencies=[Depends(ensure_permission(Permission.DomainProblem.view_config))],
)
async def clone_problem(
    problem_clone: models.ProblemClone,
    domain: models.Domain = Depends(parse_domain_from_auth),
    user: models.User = Depends(parse_user_from_auth),
    auth: Authentication = Depends(),
) -> StandardListResponse[models.Problem]:
    problems = [await parse_problem(oid, auth) for oid in problem_clone.problems]
    problem_set = await parse_problem_set(problem_clone.problem_set, auth)
    new_group = problem_clone.new_group
    try:
        async with transactions.in_transaction():
            res = []
            for problem in problems:
                if new_group:
                    problem_group = models.ProblemGroup(
                        **models.ProblemGroup().to_model()
                    )
                    await problem_group.commit()
                else:
                    problem_group = await problem.problem_group.fetch()
                new_problem = models.Problem(
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
                res.append(models.Problem.from_orm(new_problem))
                logger.info("problem cloned: %s", new_problem)
    except Exception as e:
        logger.exception("problems clone to problem set failed: %s", problem_set)
        raise e
    return StandardListResponse(res)


@router.post(
    "/{problem}",
    dependencies=[Depends(ensure_permission(Permission.DomainProblem.submit))],
)
async def submit_solution_to_problem(
    code_type: models.RecordCodeType = Form(...),
    file: UploadFile = File(...),
    problem: models.Problem = Depends(parse_problem),
    domain: models.Domain = Depends(parse_domain_from_auth),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[models.Record]:
    if domain.id != problem.domain:
        # TODO: test whether problem.domain is object id and add other error code
        raise BizError(ErrorCode.ProblemNotFoundError)
    try:
        # gfs = AsyncIOMotorGridFSBucket(get_db())
        #
        file_id = None
        record = models.Record(
            domain=problem.domain,
            problem=problem.id,
            user=user.id,
            code_type=code_type,
            code=file_id,
            judge_category=[],
            submit_at=datetime.utcnow(),
            cases=[models.RecordCase() for i in range(10)],  # TODO: modify later
        )
        record_model = models.Record(**record.to_model())
        await record_model.commit()
        problem.num_submit += 1
        await problem.commit()
        logger.info("problem submitted with record: %s", record_model.id)
    except Exception as e:
        logger.exception("problem submission failed: %s", problem.id)
        raise e
    record_schema = models.Record.from_orm(record_model)
    http_url = generate_url(
        records.router_prefix, records.router_name, record_schema.id
    )
    celery_app.send_task("joj.tiger.compile", args=[record_schema.dict(), http_url])
    return StandardResponse(record_schema)
