from typing import List, Optional
from uuid import UUID

from celery import Celery
from fastapi import BackgroundTasks, Depends
from loguru import logger
from sqlmodel.ext.asyncio.session import AsyncSession

from joj.horse import models, schemas
from joj.horse.schemas import Empty, StandardListResponse, StandardResponse
from joj.horse.schemas.auth import Authentication, get_domain
from joj.horse.schemas.permission import Permission
from joj.horse.services.celery_app import celery_app_dependency
from joj.horse.services.db import db_session_dependency
from joj.horse.services.lakefs import LakeFSProblemConfig
from joj.horse.utils.errors import ForbiddenError
from joj.horse.utils.fastapi.router import MyRouter
from joj.horse.utils.parser import (
    parse_domain_from_auth,
    parse_ordering_query,
    parse_pagination_query,
    parse_problem,
    parse_problem_without_validation,
    parse_user_from_auth,
    parse_view_hidden_problem,
)

router = MyRouter()
router_name = "domains/{domain}/problems"
router_tag = "problem"


@router.get("", permissions=[Permission.DomainProblem.view])
async def list_problems(
    domain: models.Domain = Depends(parse_domain_from_auth),
    ordering: schemas.OrderingQuery = Depends(parse_ordering_query()),
    pagination: schemas.PaginationQuery = Depends(parse_pagination_query),
    include_hidden: bool = Depends(parse_view_hidden_problem),
    user: schemas.User = Depends(parse_user_from_auth),
) -> StandardListResponse[schemas.ProblemWithLatestRecord]:
    statement = domain.find_problems_statement(include_hidden)
    problems, count = await models.Problem.execute_list_statement(
        statement, ordering, pagination
    )
    result = await models.Problem.get_problems_with_record_states(
        result_cls=schemas.ProblemWithLatestRecord,
        problem_set_id=None,
        problems=problems,
        user_id=user.id,
    )
    return StandardListResponse(result, count)


@router.post("", permissions=[Permission.DomainProblem.create])
async def create_problem(
    problem_create: schemas.ProblemCreate,
    background_tasks: BackgroundTasks,
    domain: models.Domain = Depends(parse_domain_from_auth),
    user: schemas.User = Depends(parse_user_from_auth),
    session: AsyncSession = Depends(db_session_dependency),
) -> StandardResponse[schemas.ProblemDetail]:
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


@router.get("/{problem}", permissions=[Permission.DomainProblem.view])
async def get_problem(
    problem: models.Problem = Depends(parse_problem),
    user: schemas.User = Depends(parse_user_from_auth),
) -> StandardResponse[schemas.ProblemDetailWithLatestRecord]:
    record = await models.Record.get_user_latest_record(
        problem_set_id=None, problem_id=problem.id, user_id=user.id
    )
    result = schemas.ProblemDetailWithLatestRecord(
        **problem.dict(), latest_record=record
    )
    return StandardResponse(result)


@router.delete("/{problem}", permissions=[Permission.DomainProblem.edit])
async def delete_problem(
    problem: models.Problem = Depends(parse_problem),
) -> StandardResponse[Empty]:
    await problem.delete_model()
    return StandardResponse()


@router.patch("/{problem}", permissions=[Permission.DomainProblem.edit])
async def update_problem(
    problem_edit: schemas.ProblemEdit = Depends(schemas.ProblemEdit.edit_dependency),
    problem: models.Problem = Depends(parse_problem),
) -> StandardResponse[schemas.Problem]:
    problem.update_from_dict(problem_edit.dict())
    await problem.save_model()
    return StandardResponse(problem)


@router.post("/clone", permissions=[Permission.DomainProblem.view_config])
async def clone_problem(
    problem_clone: schemas.ProblemClone,
    domain: models.Domain = Depends(parse_domain_from_auth),
    user: schemas.User = Depends(parse_user_from_auth),
    auth: Authentication = Depends(),
    session: AsyncSession = Depends(db_session_dependency),
) -> StandardListResponse[schemas.Problem]:
    from_domain = await get_domain(problem_clone.from_domain)
    if from_domain.tag != domain.tag:
        raise ForbiddenError(message="relevant domain Permission Denied.")
    problems: List[models.Problem] = [
        parse_problem(await parse_problem_without_validation(oid, from_domain), auth)
        for oid in problem_clone.problems
    ]
    try:
        new_problems = []
        for problem in problems:
            problem_group_id: Optional[UUID]
            if problem_clone.new_group:
                problem_group = models.ProblemGroup()
                session.sync_session.add(problem_group)
                problem_group_id = problem_group.id
            else:
                problem_group_id = problem.problem_group_id
            new_problem = models.Problem(
                domain_id=domain.id,
                owner_id=user.id,
                title=problem.title,
                content=problem.content,
                url=problem.url if from_domain.id != domain.id else "",
                problem_group_id=problem_group_id,
            )
            session.sync_session.add(new_problem)
            new_problems.append(new_problem)
            logger.info(f"problem cloned: {new_problem}")
        await session.commit()
    except Exception as e:
        logger.exception(f"problems clone failed: {[problem for problem in problems]}")
        raise e
    res = []
    for problem in new_problems:
        await session.refresh(problem)
        res.append(models.Problem.from_orm(problem))
    return StandardListResponse(res)


@router.post("/{problem}", permissions=[Permission.DomainProblem.submit])
async def submit_solution_to_problem(
    background_tasks: BackgroundTasks,
    celery_app: Celery = Depends(celery_app_dependency),
    problem_submit: schemas.ProblemSolutionSubmit = Depends(
        schemas.ProblemSolutionSubmit.form_dependency
    ),
    problem: models.Problem = Depends(parse_problem),
    user: schemas.User = Depends(parse_user_from_auth),
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
