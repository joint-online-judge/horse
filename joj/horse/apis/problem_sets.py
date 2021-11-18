from datetime import datetime, timedelta
from typing import List

from fastapi import Depends
from loguru import logger

from joj.horse import models, schemas
from joj.horse.schemas import Empty, Operation, StandardListResponse, StandardResponse
from joj.horse.schemas.permission import Permission
from joj.horse.utils.auth import DomainAuthentication, ensure_permission
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.parser import (
    parse_domain_from_auth,
    parse_edit_schema,
    parse_ordering_query,
    parse_pagination_query,
    parse_problem,
    parse_problem_set,
    parse_problem_set_factory,
    parse_problem_set_with_time,
    parse_problem_without_validation,
    parse_user_from_auth,
    parse_view_hidden_problem_set,
)
from joj.horse.utils.router import MyRouter

router = MyRouter()
router_name = "domains/{domain}/problem_sets"
router_tag = "problem set"
router_prefix = "/api/v1"


@router.get(
    "", dependencies=[Depends(ensure_permission(Permission.DomainProblemSet.view))]
)
async def list_problem_sets(
    domain: models.Domain = Depends(parse_domain_from_auth),
    ordering: schemas.OrderingQuery = Depends(parse_ordering_query(["name"])),
    pagination: schemas.PaginationQuery = Depends(parse_pagination_query),
    include_hidden: bool = Depends(parse_view_hidden_problem_set),
) -> StandardListResponse[schemas.ProblemSet]:
    statement = domain.find_problem_sets_statement(include_hidden)
    problem_sets, count = await models.ProblemSet.execute_list_statement(
        statement, ordering, pagination
    )
    return StandardListResponse(problem_sets, count)


@router.post(
    "", dependencies=[Depends(ensure_permission(Permission.DomainProblemSet.create))]
)
async def create_problem_set(
    problem_set_create: schemas.ProblemSetCreate,
    domain: models.Domain = Depends(parse_domain_from_auth),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[schemas.ProblemSet]:
    problem_set = models.ProblemSet(
        **problem_set_create.dict(),
        domain_id=domain.id,
        owner_id=user.id,
    )
    logger.info(f"create problem set: {problem_set}")
    await problem_set.save_model()
    return StandardResponse(problem_set)


@router.get(
    "/{problemSet}",
    dependencies=[Depends(ensure_permission(Permission.DomainProblemSet.view))],
)
async def get_problem_set(
    problem_set: models.ProblemSet = Depends(
        parse_problem_set_factory(load_problems=True, load_links=True)
    ),
) -> StandardResponse[schemas.ProblemSetDetail]:
    logger.info(problem_set.problem_problem_set_links)
    logger.info(problem_set.problems)
    return StandardResponse(problem_set)


@router.delete(
    "/{problemSet}",
    dependencies=[Depends(ensure_permission(Permission.DomainProblemSet.edit))],
    deprecated=True,
)
async def delete_problem_set(
    problem_set: models.ProblemSet = Depends(parse_problem_set),
) -> StandardResponse[Empty]:
    await problem_set.delete_model()
    return StandardResponse()


@router.patch(
    "/{problemSet}",
    dependencies=[Depends(ensure_permission(Permission.DomainProblemSet.edit))],
)
async def update_problem_set(
    problem_set_edit: schemas.ProblemSetEdit = Depends(
        parse_edit_schema(schemas.ProblemSetEdit)
    ),
    problem_set: models.ProblemSet = Depends(parse_problem_set),
) -> StandardResponse[schemas.ProblemSet]:
    problem_set.update_from_dict(problem_set_edit.dict())
    await problem_set.save_model()
    return StandardResponse(problem_set)


@router.post(
    "/{problemSet}/problem",
    dependencies=[Depends(ensure_permission(Permission.DomainProblemSet.edit))],
)
async def add_problem_in_problem_set(
    add_problem: schemas.ProblemSetAddProblem,
    problem_set: models.ProblemSet = Depends(
        parse_problem_set_factory(load_links=True)
    ),
    domain_auth: DomainAuthentication = Depends(DomainAuthentication),
) -> StandardResponse[schemas.ProblemSet]:
    problem = await parse_problem(add_problem.problem, domain_auth)
    await problem_set.operate_problem(problem, Operation.Create, add_problem.position)
    return StandardResponse(problem_set)


@router.get(
    "/{problemSet}/problem/{problem}",
    dependencies=[Depends(ensure_permission(Permission.DomainProblemSet.view))],
)
async def get_problem_in_problem_set(
    problem_set: models.ProblemSet = Depends(parse_problem_set),
    problem: models.Problem = Depends(parse_problem_without_validation),
) -> StandardResponse[schemas.ProblemDetail]:
    await problem_set.operate_problem(problem, Operation.Read)
    return StandardResponse(problem)


@router.patch(
    "/{problemSet}/problem/{problem}",
    dependencies=[Depends(ensure_permission(Permission.DomainProblemSet.edit))],
)
async def update_problem_in_problem_set(
    update_problem: schemas.ProblemSetUpdateProblem,
    problem_set: models.ProblemSet = Depends(
        parse_problem_set_factory(load_links=True)
    ),
    problem: models.Problem = Depends(parse_problem),
) -> StandardResponse[schemas.ProblemSet]:
    await problem_set.operate_problem(
        problem, Operation.Update, update_problem.position
    )
    return StandardResponse(problem_set)


@router.delete(
    "/{problemSet}/problem/{problem}",
    dependencies=[Depends(ensure_permission(Permission.DomainProblemSet.edit))],
)
async def delete_problem_in_problem_set(
    problem_set: models.ProblemSet = Depends(
        parse_problem_set_factory(load_links=True)
    ),
    problem: models.Problem = Depends(parse_problem),
) -> StandardResponse[schemas.ProblemSet]:
    await problem_set.operate_problem(problem, Operation.Delete)
    return StandardResponse(problem_set)


@router.get("/{problemSet}/scoreboard", deprecated=True)
async def get_scoreboard(
    problem_set: models.ProblemSet = Depends(parse_problem_set_with_time),
    domain: models.Domain = Depends(parse_domain_from_auth),
) -> StandardResponse[schemas.ScoreBoard]:
    if problem_set.scoreboard_hidden:
        raise BizError(ErrorCode.ScoreboardHiddenBadRequestError)
    # domain: models.Domain = await problem_set.domain.fetch()
    cursor = models.DomainUser.cursor_join(
        field="user", condition={"domain": domain.id}
    )
    users = await models.User.to_list(cursor)
    results: List[models.UserScore] = []
    problem_ids: List[str] = []
    firstUser = True
    for user in users:
        scores: List[models.Score] = []
        total_score = 0
        total_time_spent = timedelta(0)
        problem: models.Problem
        async for problem in models.Problem.find({"problem_set": problem_set.id}):
            if firstUser:
                problem_ids.append(problem.id)
            record_model: schemas.Record = await schemas.Record.find_one(
                # {
                #     "user": str(user.id),
                #     "problem": problem.id,
                #     "submit_at": {"$gte": problem_set.available_time},
                #     "status": {"$nin": [RecordStatus.waiting, RecordStatus.judging]},
                # },
                sort=[("submit_at", "DESCENDING")],
            )
            tried = record_model is not None
            record = schemas.Record.from_orm(record_model) if record_model else None
            score = 0
            time = datetime(1970, 1, 1)
            time_spent = datetime.utcnow() - problem_set.available_time
            full_score = 1000  # TODO: modify later
            if record is not None:
                score = record.score
                time = record.submit_at
                time_spent = record_model.submit_at - problem_set.available_time
            total_score += score
            total_time_spent += time_spent
            scores.append(
                models.Score(
                    score=score,
                    time=time,
                    full_score=full_score,
                    time_spent=time_spent,
                    tried=tried,
                )
            )
        user_score = models.UserScore(
            user=user,
            total_score=total_score,
            total_time_spent=total_time_spent,
            scores=scores,
        )
        results.append(user_score)
        firstUser = False
    results.sort(key=lambda x: (x.total_score, x.total_time_spent))
    return StandardResponse(models.ScoreBoard(results=results, problem_ids=problem_ids))
