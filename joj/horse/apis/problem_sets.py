from datetime import datetime, timedelta
from typing import List

from bson.objectid import ObjectId
from fastapi import Depends, Query
from pydantic.schema import schema
from uvicorn.config import logger

from joj.horse import models, schemas
from joj.horse.schemas import Empty, StandardResponse
from joj.horse.schemas.problem_set import ListProblemSets
from joj.horse.schemas.score import ListUserScores, Score, UserScore
from joj.horse.utils.auth import Authentication
from joj.horse.utils.db import generate_join_pipeline, instance
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.parser import parse_problem_set
from joj.horse.utils.router import MyRouter

router = MyRouter()
router_name = "problem_sets"
router_tag = "problem set"
router_prefix = "/api/v1"


@router.get("")
async def list_problem_sets(
    required_labels: List[str] = Query([]), auth: Authentication = Depends()
) -> StandardResponse[ListProblemSets]:
    return StandardResponse(
        ListProblemSets(
            results=[
                schemas.ProblemSet.from_orm(problem_set)
                async for problem_set in models.ProblemSet.find({"owner": auth.user.id})
                if all(label in problem_set.labels for label in required_labels)
            ]
        )
    )


@router.post("")
async def create_problem_set(
    problem_set: schemas.ProblemSetCreate, auth: Authentication = Depends()
) -> StandardResponse[schemas.ProblemSet]:
    if auth.user is None:
        raise BizError(ErrorCode.InvalidAuthenticationError)

    # use transaction for multiple operations
    try:
        async with instance.session() as session:
            async with session.start_transaction():
                domain = await models.Domain.find_by_url_or_id(problem_set.domain)
                problems_models = [
                    await models.Problem.find_by_id(problem)
                    for problem in problem_set.problems
                ]
                for i, (problem_id, problem_model) in enumerate(
                    zip(problem_set.problems, problems_models)
                ):
                    if problem_model is None:
                        raise BizError(ErrorCode.ProblemNotFoundError)
                    problems_models[i] = problem_model.id
                logger.info("problems_models: %s", problems_models)
                problem_set = schemas.ProblemSet(
                    title=problem_set.title,
                    content=problem_set.content,
                    hidden=problem_set.hidden,
                    domain=domain.id,
                    owner=auth.user.id,
                    problems=problems_models,
                )
                problem_set = models.ProblemSet(**problem_set.to_model())
                await problem_set.commit()
                logger.info("problem set created: %s", problem_set)

    except Exception as e:
        logger.error("problem set creation failed: %s", problem_set.title)
        raise e
    return StandardResponse(schemas.ProblemSet.from_orm(problem_set))


@router.get("/{problem_set}")
async def get_problem_set(
    problem_set: models.ProblemSet = Depends(parse_problem_set),
) -> StandardResponse[schemas.ProblemSet]:
    return StandardResponse(schemas.ProblemSet.from_orm(problem_set))


@router.delete("/{problem_set}")
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
    problem_set: models.ProblemSet = Depends(parse_problem_set),
) -> StandardResponse[ListUserScores]:
    problems = [
        await models.Problem.find_by_id(problem.pk) for problem in problem_set.problems
    ]
    domain = await problem_set.domain.fetch()
    pipeline = generate_join_pipeline(field="user", condition={"domain": domain.id})
    users = [
        schemas.User.from_orm(
            await models.DomainUser.build_from_mongo(domain_user).user.fetch()
        )
        async for domain_user in models.DomainUser.aggregate(pipeline)
    ]
    results: List[UserScore] = []
    for i, user in enumerate(users):
        scores: List[Score] = []
        total_score = 0
        total_time_spent = timedelta(0)
        for problem in problems:
            record_model = await models.Record.find_one(
                {"user": ObjectId(user.id), "problem": problem.id}
            )  # TODO: find the latest record
            tried = record_model is not None
            record = schemas.Record.from_orm(record_model) if record_model else None
            score = 0
            time = datetime(1970, 1, 1)
            time_spent = timedelta(hours=1)  # TODO: modify later
            full_score = 1000  # TODO: modify later
            if record is not None:
                score = record.score
                time = record.submit_at
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
            rank=i + 1,  # TODO: modify later
            user=user,
            total_score=total_score,
            total_time_spent=total_time_spent,
            scores=scores,
        )
        results.append(user_score)
    ...  # TODO: sort rank here
    return StandardResponse(ListUserScores(results=results))
