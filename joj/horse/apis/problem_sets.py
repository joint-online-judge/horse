from datetime import datetime, timedelta
from typing import List

from fastapi import Depends
from loguru import logger

from joj.horse import models, schemas
from joj.horse.schemas import Empty, StandardListResponse, StandardResponse
from joj.horse.schemas.permission import Permission
from joj.horse.utils.auth import Authentication, ensure_permission
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.parser import (
    parse_domain_from_auth,
    parse_pagination_query,
    parse_problem_set,
    parse_problem_set_with_time,
    parse_user_from_auth,
)
from joj.horse.utils.router import MyRouter

router = MyRouter()
router_name = "domains/{domain}/problem_sets"
router_tag = "problem set"
router_prefix = "/api/v1"


@router.get(
    "", dependencies=[Depends(ensure_permission(Permission.DomainProblem.view))]
)
async def list_problem_sets(
    domain: models.Domain = Depends(parse_domain_from_auth),
    query: schemas.PaginationQuery = Depends(parse_pagination_query),
    auth: Authentication = Depends(),
) -> StandardListResponse[models.ProblemSet]:
    condition = {"owner": auth.user.id}
    if domain is not None:
        condition["domain"] = str(domain.id)
    cursor = models.ProblemSet.cursor_find(condition, query)
    res = await models.ProblemSet.to_list(cursor)
    return StandardResponse(res)


@router.post(
    "", dependencies=[Depends(ensure_permission(Permission.DomainProblem.create))]
)
async def create_problem_set(
    problem_set_create: models.ProblemSetCreate,
    domain: models.Domain = Depends(parse_domain_from_auth),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[models.ProblemSet]:
    problem_set = models.ProblemSet(
        **problem_set_create.dict(),
        domain_id=domain.id,
        owner_id=user.id,
    )
    logger.info(f"create problem set: {problem_set}")
    await problem_set.save_model()
    return StandardResponse(problem_set)


@router.get("/{problem_set}")
async def get_problem_set(
    problem_set: models.ProblemSet = Depends(parse_problem_set),
) -> StandardResponse[models.ProblemSet]:
    return StandardResponse(problem_set)


@router.delete("/{problem_set}", deprecated=True)
async def delete_problem_set(
    problem_set: models.ProblemSet = Depends(parse_problem_set),
) -> StandardResponse[Empty]:
    await problem_set.delete_model()
    return StandardResponse()


@router.patch("/{problem_set}")
async def update_problem_set(
    edit_problem_set: models.ProblemSetEdit,
    problem_set: models.ProblemSet = Depends(parse_problem_set),
) -> StandardResponse[models.ProblemSet]:
    problem_set.update_from_dict(edit_problem_set.dict())
    await problem_set.save_model()
    return StandardResponse(problem_set)


@router.get("/{problem_set}/scoreboard")
async def get_scoreboard(
    problem_set: models.ProblemSet = Depends(parse_problem_set_with_time),
    domain: models.Domain = Depends(parse_domain_from_auth),
) -> StandardResponse[models.ScoreBoard]:
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
            record_model: models.Record = await models.Record.find_one(
                # {
                #     "user": str(user.id),
                #     "problem": problem.id,
                #     "submit_at": {"$gte": problem_set.available_time},
                #     "status": {"$nin": [RecordStatus.waiting, RecordStatus.judging]},
                # },
                sort=[("submit_at", "DESCENDING")],
            )
            tried = record_model is not None
            record = models.Record.from_orm(record_model) if record_model else None
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
