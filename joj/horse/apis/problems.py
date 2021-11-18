from datetime import datetime

from fastapi import BackgroundTasks, Depends, File, Form, UploadFile
from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from joj.horse import models, schemas
from joj.horse.apis import records
from joj.horse.schemas import Empty, StandardListResponse, StandardResponse
from joj.horse.schemas.permission import Permission
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
    ordering: schemas.OrderingQuery = Depends(parse_ordering_query(["name"])),
    pagination: schemas.PaginationQuery = Depends(parse_pagination_query),
    include_hidden: bool = Depends(parse_view_hidden_problem),
) -> StandardListResponse[schemas.Problem]:
    statement = domain.find_problems_statement(include_hidden)
    problems, count = await models.Problem.execute_list_statement(
        statement, ordering, pagination
    )
    return StandardListResponse(problems, count)


@router.post(
    "", dependencies=[Depends(ensure_permission(Permission.DomainProblem.create))]
)
async def create_problem(
    problem_create: schemas.ProblemCreate,
    background_tasks: BackgroundTasks,
    domain: models.Domain = Depends(parse_domain_from_auth),
    user: models.User = Depends(parse_user_from_auth),
    session: AsyncSession = Depends(db_session_dependency),
) -> StandardResponse[schemas.Problem]:
    try:
        problem_group = models.ProblemGroup()
        session.sync_session.add(problem_group)
        logger.info(f"problem group created: {problem_group}")
        problem = models.Problem(
            **problem_create.dict(),
            domain_id=domain.id,
            owner_id=user.id,
            problem_group_id=problem_group.id,
        )
        session.sync_session.add(problem)
        logger.info(f"problem created: {problem}")
        await session.commit()
        await session.refresh(problem)
    except Exception as e:
        logger.exception(f"problem creation failed: {problem_create}")
        raise e
    lakefs_problem_config = LakeFSProblemConfig(problem)
    background_tasks.add_task(lakefs_problem_config.ensure_branch)
    return StandardResponse(problem)


@router.get(
    "/{problem}",
    dependencies=[Depends(ensure_permission(Permission.DomainProblem.view))],
)
async def get_problem(
    problem: models.Problem = Depends(parse_problem),
) -> StandardResponse[schemas.ProblemDetail]:
    return StandardResponse(problem)


@router.delete(
    "/{problem}",
    dependencies=[Depends(ensure_permission(Permission.DomainProblem.edit))],
)
async def delete_problem(
    problem: models.Problem = Depends(parse_problem),
) -> StandardResponse[Empty]:
    await problem.delete_model()
    return StandardResponse()


@router.patch(
    "/{problem}",
    dependencies=[Depends(ensure_permission(Permission.DomainProblem.edit))],
)
async def update_problem(
    problem_edit: schemas.ProblemEdit = Depends(schemas.ProblemEdit.edit_dependency),
    problem: models.Problem = Depends(parse_problem),
) -> StandardResponse[schemas.Problem]:
    problem.update_from_dict(problem_edit.dict())
    await problem.save_model()
    return StandardResponse(problem)


@router.patch(
    "/{problem}/config",
    dependencies=[Depends(ensure_permission(Permission.DomainProblem.view_config))],
)
async def update_problem_config(
    config: UploadFile = File(...), problem: models.Problem = Depends(parse_problem)
) -> StandardResponse[schemas.Problem]:
    return StandardResponse(problem)


@router.post(
    "/clone",
    dependencies=[Depends(ensure_permission(Permission.DomainProblem.view_config))],
)
async def clone_problem(
    problem_clone: schemas.ProblemClone,
    domain: models.Domain = Depends(parse_domain_from_auth),
    user: models.User = Depends(parse_user_from_auth),
    auth: Authentication = Depends(),
) -> StandardListResponse[schemas.Problem]:
    problems = [await parse_problem(oid, auth) for oid in problem_clone.problems]
    problem_set = await parse_problem_set(problem_clone.problem_set, auth)
    new_group = problem_clone.new_group
    try:
        res = []
        for problem in problems:
            if new_group:
                problem_group = models.ProblemGroup(**models.ProblemGroup().to_model())
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
            logger.info(f"problem cloned: {new_problem}")
    except Exception as e:
        logger.exception(f"problems clone to problem set failed: {problem_set}")
        raise e
    return StandardListResponse(res)


@router.post(
    "/{problem}",
    dependencies=[Depends(ensure_permission(Permission.DomainProblem.submit))],
)
async def submit_solution_to_problem(
    code_type: schemas.RecordCodeType = Form(...),
    file: UploadFile = File(...),
    problem: models.Problem = Depends(parse_problem),
    domain: models.Domain = Depends(parse_domain_from_auth),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[schemas.Record]:
    if domain.id != problem.domain:
        # TODO: test whether problem.domain is object id and add other error code
        raise BizError(ErrorCode.ProblemNotFoundError)
    try:
        # gfs = AsyncIOMotorGridFSBucket(get_db())
        #
        file_id = None
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
        record_model = schemas.Record(**record.to_model())
        await record_model.commit()
        problem.num_submit += 1
        await problem.commit()
        logger.info(f"problem submitted with record: {record_model.id}")
    except Exception as e:
        logger.exception(f"problem submission failed: {problem.id}")
        raise e
    record_schema = schemas.Record.from_orm(record_model)
    http_url = generate_url(
        records.router_prefix, records.router_name, record_schema.id
    )
    celery_app.send_task("joj.tiger.compile", args=[record_schema.dict(), http_url])
    return StandardResponse(record_schema)
