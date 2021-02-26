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


async def parse_pid(problem: str, auth: Authentication = Depends()) -> models.User:
    problem_model = await models.Problem.find_by_id(problem)
    if problem_model and problem_model.owner == auth.user:
        return problem_model
    raise errors.ProblemNotFoundError(problem_model)
