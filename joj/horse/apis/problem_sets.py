import time
from datetime import datetime, timedelta
from typing import List, Optional

import pymongo
from bson.objectid import ObjectId
from fastapi import Depends, Query
from marshmallow.exceptions import ValidationError
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.schemas import Empty, StandardResponse
from joj.horse.schemas.base import PydanticObjectId
from joj.horse.schemas.problem_set import ListProblemSets
from joj.horse.schemas.record import RecordStatus
from joj.horse.schemas.score import Score, ScoreBoard, UserScore
from joj.horse.utils.auth import Authentication
from joj.horse.utils.db import generate_join_pipeline, instance
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.parser import (
    parse_problem_set,
    parse_problem_set_with_time,
    parse_query,
)
from joj.horse.utils.router import MyRouter

router = MyRouter()
router_name = "problem_sets"
router_tag = "problem set"
router_prefix = "/api/v1"


@router.get("")
async def list_problem_sets(
    domain_id: Optional[PydanticObjectId] = Query(None),
    query: schemas.BaseFilter = Depends(parse_query),
    auth: Authentication = Depends(),
) -> StandardResponse[ListProblemSets]:
    filter = {"owner": auth.user.id}
    if domain_id is not None:
        filter["domain"] = ObjectId(domain_id)
    res = await schemas.ProblemSet.to_list(filter, query)
    return StandardResponse(ListProblemSets(results=res))


@router.post("")
async def create_problem_set(
    problem_set: schemas.ProblemSetCreate, auth: Authentication = Depends()
) -> StandardResponse[schemas.ProblemSet]:
    if ObjectId.is_valid(problem_set.url):
        raise BizError(ErrorCode.InvalidUrlError)
    none_url = problem_set.url is None
    if problem_set.url is None:
        problem_set.url = str(time.time()).replace(".", "")
    # use transaction for multiple operations
    try:
        async with instance.session() as session:
            async with session.start_transaction():
                domain: models.Domain = await models.Domain.find_by_url_or_id(
                    problem_set.domain
                )
                problem_set_schema = schemas.ProblemSet(
                    title=problem_set.title,
                    content=problem_set.content,
                    hidden=problem_set.hidden,
                    domain=domain.id,
                    owner=auth.user.id,
                    scoreboard_hidden=problem_set.scoreboard_hidden,
                    available_time=problem_set.available_time,
                    due_time=problem_set.due_time,
                )
                problem_set_model = models.ProblemSet(**problem_set_schema.to_model())
                await problem_set_model.commit()
                if none_url:
                    problem_set_model.url = str(problem_set_model.id)
                    await problem_set_model.commit()
                logger.info("problem set created: %s", problem_set_model)
    except ValidationError:
        raise BizError(ErrorCode.UrlNotUniqueError)
    except Exception as e:
        logger.error("problem set creation failed: %s", problem_set.title)
        raise e
    return StandardResponse(schemas.ProblemSet.from_orm(problem_set_model))


@router.get("/{problem_set}")
async def get_problem_set(
    problem_set: models.ProblemSet = Depends(parse_problem_set_with_time),
) -> StandardResponse[schemas.ProblemSet]:
    return StandardResponse(schemas.ProblemSet.from_orm(problem_set))


@router.delete("/{problem_set}", deprecated=True)
async def delete_problem_set(
    problem_set: models.ProblemSet = Depends(parse_problem_set),
) -> StandardResponse[Empty]:
    await problem_set.delete()
    return StandardResponse()


@router.patch("/{problem_set}")
async def update_problem_set(
    edit_problem_set: schemas.ProblemSetEdit,
    problem_set: models.ProblemSet = Depends(parse_problem_set),
) -> StandardResponse[schemas.ProblemSet]:
    problem_set.update_from_schema(edit_problem_set)
    await problem_set.commit()
    return StandardResponse(schemas.ProblemSet.from_orm(problem_set))


@router.get("/{problem_set}/scoreboard")
async def get_scoreboard(
    problem_set: models.ProblemSet = Depends(parse_problem_set_with_time),
) -> StandardResponse[ScoreBoard]:
    if problem_set.scoreboard_hidden:
        raise BizError(ErrorCode.ScoreboardHiddenBadRequestError)
    domain = await problem_set.domain.fetch()
    pipeline = generate_join_pipeline(field="user", condition={"domain": domain.id})
    users = [
        schemas.User.from_orm(
            await models.DomainUser.build_from_mongo(domain_user).user.fetch()
        )
        async for domain_user in models.DomainUser.aggregate(pipeline)
    ]
    results: List[UserScore] = []
    problem_ids: List[PydanticObjectId] = []
    firstUser = True
    for i, user in enumerate(users):
        scores: List[Score] = []
        total_score = 0
        total_time_spent = timedelta(0)
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
                sort=[("submit_at", pymongo.DESCENDING)],
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
