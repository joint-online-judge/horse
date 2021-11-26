from celery import Celery
from fastapi import BackgroundTasks, Depends
from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from joj.horse import models, schemas
from joj.horse.schemas import Empty, StandardListResponse, StandardResponse
from joj.horse.schemas.permission import Permission
from joj.horse.utils.auth import Authentication, ensure_permission
from joj.horse.utils.db import db_session_dependency
from joj.horse.utils.lakefs import LakeFSProblemConfig
from joj.horse.utils.parser import (
    parse_domain_from_auth,
    parse_ordering_query,
    parse_pagination_query,
    parse_problem,
    parse_problem_set,
    parse_problem_without_validation,
    parse_user_from_auth,
    parse_view_hidden_problem,
)
from joj.horse.utils.router import MyRouter
from joj.horse.utils.tasks import celery_app_dependency

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


# @router.patch(
#     "/{problem}/config",
#     dependencies=[Depends(ensure_permission(Permission.DomainProblem.view_config))],
# )
# async def update_problem_config(
#     config: UploadFile = File(...), problem: models.Problem = Depends(parse_problem)
# ) -> StandardResponse[schemas.Problem]:
#     return StandardResponse(problem)


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
    # TODO: transaction here
    problems = [
        await parse_problem(await parse_problem_without_validation(oid, domain), auth)
        for oid in problem_clone.problems
    ]
    problem_set = await parse_problem_set(problem_clone.problem_set, domain)
    new_group = problem_clone.new_group
    try:
        res = []
        for problem in problems:
            if new_group:
                problem_group = models.ProblemGroup()
                # FIXME: seems other objects are distroyed
                await problem_group.save_model()
                problem_group_id = problem_group.id
            else:
                problem_group_id = problem.problem_group_id
            new_problem = models.Problem(
                domain_id=domain.id,
                owner_id=user.id,
                title=problem.title,
                content=problem.content,
                problem_group_id=problem_group_id,
                problem_set_id=problem_set.id,
            )
            await new_problem.save_model()
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
    background_tasks: BackgroundTasks,
    celery_app: Celery = Depends(celery_app_dependency),
    problem_submit: schemas.ProblemSolutionSubmit = Depends(
        schemas.ProblemSolutionSubmit.form_dependency
    ),
    problem: models.Problem = Depends(parse_problem),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[schemas.Record]:
    record = await models.Record.submit(
        background_tasks=background_tasks,
        celery_app=celery_app,
        problem_submit=problem_submit,
        problem_set=None,
        problem=problem,
        user=user,
    )
    logger.info("create record: {}", record)
    return StandardResponse(record)
