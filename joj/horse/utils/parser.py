from typing import Optional

from fastapi import Depends, Query

from joj.horse import models
from joj.horse.utils import errors
from joj.horse.utils.auth import Authentication


async def parse_uid(
    uid: Optional[str] = Query("me", description="uid or 'me'"),
    auth: Authentication = Depends(),
) -> models.User:
    if uid == "me":
        if auth.user:
            return auth.user
        raise errors.InvalidAuthenticationError()
    else:
        user = await models.User.find_by_id(uid)
        if user:
            return user
        raise errors.UserNotFoundError(uid)


async def parse_problem(
    problem: str, auth: Authentication = Depends()
) -> models.Problem:
    problem_model = await models.Problem.find_by_id(problem)
    if problem_model and problem_model.owner == auth.user:
        return problem_model
    raise errors.ProblemNotFoundError(problem)


async def parse_problem_set(
    problem_set: str, auth: Authentication = Depends()
) -> models.ProblemSet:
    problem_set_model = await models.Problem.find_by_id(problem_set)
    if problem_set_model and problem_set_model.owner == auth.user:
        return problem_set_model
    raise errors.ProblemSetNotFoundError(problem_set)


async def parse_record(record: str, auth: Authentication = Depends()) -> models.Record:
    record_model = await models.Record.find_by_id(record)
    if record_model and record_model.user == auth.user:
        return record_model
    raise errors.RecordNotFoundError(record)
