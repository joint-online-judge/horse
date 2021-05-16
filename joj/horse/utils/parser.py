from datetime import datetime
from typing import Optional

from fastapi import Depends, Path, Query

from joj.horse import models
from joj.horse.schemas.query import BaseFilter, SortEnum
from joj.horse.utils.auth import Authentication, DomainAuthentication
from joj.horse.utils.errors import BizError, ErrorCode


async def parse_uid(
    uid: str = Query("me", description="uid or 'me'"), auth: Authentication = Depends()
) -> models.User:
    if uid == "me":
        if auth.user:
            return auth.user
        raise BizError(ErrorCode.InvalidAuthenticationError)
    else:
        user = await models.User.find_by_id(uid)
        if user:
            return user
        raise BizError(ErrorCode.UserNotFoundError)


async def parse_uid_or_none(
    uid: Optional[str] = Query("", description="uid or 'me' or empty"),
    auth: Authentication = Depends(),
) -> Optional[models.User]:
    return await parse_uid(uid, auth) if uid else None


async def parse_problem(
    problem: str, auth: Authentication = Depends()
) -> models.Problem:
    problem_model = await models.Problem.find_by_id(problem)
    if problem_model and problem_model.owner == auth.user:
        return problem_model
    raise BizError(ErrorCode.ProblemNotFoundError)


async def parse_problem_set(
    problem_set: str, auth: Authentication = Depends()
) -> models.ProblemSet:
    problem_set_model = await models.ProblemSet.find_by_id(problem_set)
    if problem_set_model and problem_set_model.owner == auth.user:
        return problem_set_model
    raise BizError(ErrorCode.ProblemSetNotFoundError)


async def parse_problem_set_with_time(
    problem_set: str, auth: Authentication = Depends()
) -> models.ProblemSet:
    # TODO: domain admin can see problem sets which are not in available period
    problem_set = await parse_problem_set(problem_set, auth)
    if datetime.utcnow() < problem_set.available_time:
        raise BizError(ErrorCode.ProblemSetBeforeAvailableError)
    if datetime.utcnow() > problem_set.due_time:
        raise BizError(ErrorCode.ProblemSetAfterDueError)
    return problem_set


async def parse_problem_group(problem_group: str) -> models.ProblemSet:
    problem_group_model = await models.ProblemGroup.find_by_id(problem_group)
    if problem_group_model:
        return problem_group_model
    raise BizError(ErrorCode.ProblemGroupNotFoundError)


async def parse_record(record: str, auth: Authentication = Depends()) -> models.Record:
    record_model = await models.Record.find_by_id(record)
    if record_model and record_model.user == auth.user:
        return record_model
    raise BizError(ErrorCode.RecordNotFoundError)


async def parse_record_judger(
    record: str, auth: Authentication = Depends()
) -> models.Record:
    record_model = await models.Record.find_by_id(record)
    if record_model:
        return record_model
    raise BizError(ErrorCode.RecordNotFoundError)


async def parse_domain(
    domain: str = Path(..., description="url or ObjectId of the domain"),
) -> models.Domain:
    domain_model = await models.Domain.find_by_url_or_id(domain)
    if domain_model:  # and domain_model.owner == auth.user:
        return domain_model
    raise BizError(ErrorCode.DomainNotFoundError)


def parse_domain_from_auth(
    domain_auth: DomainAuthentication = Depends(DomainAuthentication),
) -> models.Domain:
    return domain_auth.auth.domain


def parse_query(
    sort: Optional[SortEnum] = Query(None),
    skip: Optional[int] = Query(None),
    limit: Optional[int] = Query(None),
) -> BaseFilter:
    return BaseFilter(sort=sort, skip=skip, limit=limit)
