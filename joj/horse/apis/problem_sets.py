from datetime import datetime, timedelta
from typing import List

from bson.objectid import ObjectId
from fastapi import Depends
from marshmallow.exceptions import ValidationError
from pymongo import DESCENDING
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.schemas import Empty, StandardResponse
from joj.horse.schemas.base import PydanticObjectId
from joj.horse.schemas.permission import Permission
from joj.horse.schemas.problem_set import ListProblemSets
from joj.horse.schemas.record import RecordStatus
from joj.horse.schemas.score import Score, ScoreBoard, UserScore
from joj.horse.utils.auth import Authentication, ensure_permission
from joj.horse.utils.db import instance
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.parser import (
    parse_domain,
    parse_problem_set,
    parse_problem_set_with_time,
    parse_query,
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
    domain: models.Domain = Depends(parse_domain),
    query: schemas.BaseQuery = Depends(parse_query),
    auth: Authentication = Depends(),
) -> StandardResponse[ListProblemSets]:
    condition = {"owner": auth.user.id}
    if domain is not None:
        condition["domain"] = ObjectId(domain.id)
    cursor = models.ProblemSet.cursor_find(condition, query)
    res = await schemas.ProblemSet.to_list(cursor)
    return StandardResponse(ListProblemSets(results=res))


@router.post(
    "", dependencies=[Depends(ensure_permission(Permission.DomainProblem.create))]
)
async def create_problem_set(
    problem_set: schemas.ProblemSetCreate,
    domain: models.Domain = Depends(parse_domain),
    user: models.User = Depends(parse_user_from_auth),
) -> StandardResponse[schemas.ProblemSet]:
    try:
        async with instance.session() as session:
            async with session.start_transaction():
                problem_set_schema = schemas.ProblemSet(
                    **problem_set.dict(), domain=domain.id, owner=user.id
                )
                problem_set_model = models.ProblemSet(**problem_set_schema.to_model())
                await problem_set_model.commit()
                await problem_set_model.set_url_from_id()
                logger.info("problem set created: %s", problem_set_model)
    except ValidationError:
        raise BizError(ErrorCode.UrlNotUniqueError)
    except Exception as e:
        logger.exception("problem set creation failed: %s", problem_set.title)
        raise e
    return StandardResponse(schemas.ProblemSet.from_orm(problem_set_model))


@router.get("/{problem_set}")
async def get_problem_set(
    domain: models.Domain = Depends(parse_domain),
    problem_set: models.ProblemSet = Depends(parse_problem_set_with_time),
) -> StandardResponse[schemas.ProblemSet]:
    return StandardResponse(schemas.ProblemSet.from_orm(problem_set))


@router.delete("/{problem_set}", deprecated=True)
async def delete_problem_set(
    domain: models.Domain = Depends(parse_domain),
    problem_set: models.ProblemSet = Depends(parse_problem_set),
) -> StandardResponse[Empty]:
    await problem_set.delete()
    return StandardResponse()


@router.patch("/{problem_set}")
async def update_problem_set(
    edit_problem_set: schemas.ProblemSetEdit,
    domain: models.Domain = Depends(parse_domain),
    problem_set: models.ProblemSet = Depends(parse_problem_set),
) -> StandardResponse[schemas.ProblemSet]:
    problem_set.update_from_schema(edit_problem_set)
    await problem_set.commit()
    return StandardResponse(schemas.ProblemSet.from_orm(problem_set))


@router.get("/{problem_set}/scoreboard")
async def get_scoreboard(
    problem_set: models.ProblemSet = Depends(parse_problem_set_with_time),
    domain: models.Domain = Depends(parse_domain),
) -> StandardResponse[ScoreBoard]:
    if problem_set.scoreboard_hidden:
        raise BizError(ErrorCode.ScoreboardHiddenBadRequestError)
    # domain: models.Domain = await problem_set.domain.fetch()
    cursor = models.DomainUser.cursor_join(
        field="user", condition={"domain": domain.id}
    )
    users = await schemas.User.to_list(cursor)
    results: List[UserScore] = []
    problem_ids: List[PydanticObjectId] = []
    firstUser = True
    for user in users:
        scores: List[Score] = []
        total_score = 0
        total_time_spent = timedelta(0)
        problem: models.Problem
        async for problem in models.Problem.find({"problem_set": problem_set.id}):
            if firstUser:
                problem_ids.append(problem.id)
            record_model: models.Record = await models.Record.find_one(
                {
                    "user": ObjectId(user.id),
                    "problem": problem.id,
                    "submit_at": {"$gte": problem_set.available_time},
                    "status": {"$nin": [RecordStatus.waiting, RecordStatus.judging]},
                },
                sort=[("submit_at", DESCENDING)],
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
                Score(
                    score=score,
                    time=time,
                    full_score=full_score,
                    time_spent=time_spent,
                    tried=tried,
                )
            )
        user_score = UserScore(
            user=user,
            total_score=total_score,
            total_time_spent=total_time_spent,
            scores=scores,
        )
        results.append(user_score)
        firstUser = False
    results.sort(key=lambda x: (x.total_score, x.total_time_spent))
    return StandardResponse(ScoreBoard(results=results, problem_ids=problem_ids))
