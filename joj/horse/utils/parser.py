from datetime import datetime
from typing import Callable, List, Optional, Set

from fastapi import Depends, Path, Query

from joj.horse import models
from joj.horse.models.permission import PermissionType, ScopeType
from joj.horse.schemas.base import NoneEmptyLongStr, NoneNegativeInt, PaginationLimit
from joj.horse.schemas.query import OrderingQuery, PaginationQuery
from joj.horse.utils.auth import Authentication, DomainAuthentication, get_domain
from joj.horse.utils.errors import BizError, ErrorCode


async def parse_uid(
    uid: str = Query("me", description="'me' or ObjectId of the user"),
    auth: Authentication = Depends(),
) -> models.UserBase:
    if uid == "me":
        return parse_user_from_auth(auth)
    else:
        user = await models.User.get_or_none(id=uid)
        if user:
            return user
        raise BizError(ErrorCode.UserNotFoundError)


async def parse_uid_or_none(
    uid: Optional[str] = Query("", description="uid or 'me' or empty"),
    auth: Authentication = Depends(),
) -> Optional[models.UserBase]:
    return await parse_uid(uid, auth) if uid else None


async def parse_user_from_path_or_query(
    user: str = Path("me", description="'me' or ObjectId of the user"),
    auth: Authentication = Depends(),
) -> models.UserBase:
    return await parse_uid(user, auth)


def parse_user_from_auth(
    auth: Authentication = Depends(Authentication),
) -> models.UserBase:
    if auth.jwt.category != "user":
        raise BizError(ErrorCode.UserNotFoundError)
    return models.UserBase(
        id=auth.jwt.id,
        username=auth.jwt.username,
        email=auth.jwt.email,
        student_id=auth.jwt.student_id,
        real_name=auth.jwt.real_name,
        role=auth.jwt.role,
        is_active=auth.jwt.is_active,
    )


async def parse_domain(domain: models.Domain = Depends(get_domain)) -> models.Domain:
    return domain


async def parse_domain_role(
    role: NoneEmptyLongStr = Path(..., description="name of the domain role"),
    domain: models.Domain = Depends(parse_domain),
) -> models.DomainRole:
    domain_role_model = await models.DomainRole.find_one(
        {"domain": domain.id, "role": role}
    )
    if domain_role_model is None:
        raise BizError(ErrorCode.DomainRoleNotFoundError)
    return domain_role_model


async def parse_domain_invitation(
    invitation: str = Path(..., description="ObjectId of the domain invitation"),
) -> models.DomainInvitation:
    invitation_model = await models.DomainInvitation.find_by_id(invitation)
    if invitation_model is None:
        raise BizError(ErrorCode.DomainInvitationBadRequestError)
    return invitation_model


async def parse_problem(
    problem: str,
    domain_auth: DomainAuthentication = Depends(DomainAuthentication),
) -> models.Problem:
    problem_model = await models.Problem.find_by_domain_url_or_id(
        domain_auth.auth.domain, problem
    )
    if problem_model:
        if not problem_model.hidden or domain_auth.auth.check(
            ScopeType.DOMAIN_PROBLEM, PermissionType.view_hidden
        ):
            return problem_model
    raise BizError(ErrorCode.ProblemNotFoundError)


async def parse_problems(
    problems: List[str], auth: Authentication = Depends()
) -> List[models.Problem]:
    return [await parse_problem(oid, auth) for oid in problems]


async def parse_problem_set(
    problem_set: str = Path(..., description="url or ObjectId of the problem set"),
    auth: Authentication = Depends(),
) -> models.ProblemSet:
    problem_set_model = await models.ProblemSet.find_by_id(problem_set)
    if problem_set_model and problem_set_model.owner == auth.user:
        return problem_set_model
    raise BizError(ErrorCode.ProblemSetNotFoundError)


async def parse_problem_set_with_time(
    problem_set: str, auth: Authentication = Depends()
) -> models.ProblemSet:
    # TODO: domain admin can see problem sets which are not in available period
    problem_set_schema = await parse_problem_set(problem_set, auth)
    if datetime.utcnow() < problem_set_schema.available_time:
        raise BizError(ErrorCode.ProblemSetBeforeAvailableError)
    if datetime.utcnow() > problem_set_schema.due_time:
        raise BizError(ErrorCode.ProblemSetAfterDueError)
    return problem_set_schema


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


def parse_view_hidden_problem(
    domain_auth: DomainAuthentication = Depends(DomainAuthentication),
) -> bool:
    return domain_auth.auth.check(ScopeType.DOMAIN_PROBLEM, PermissionType.view_hidden)


def parse_view_hidden_problem_set(
    domain_auth: DomainAuthentication = Depends(DomainAuthentication),
) -> bool:
    return domain_auth.auth.check(
        ScopeType.DOMAIN_PROBLEM_SET, PermissionType.view_hidden
    )


class OrderingQueryParser:
    def __init__(self, ordering_fields: Optional[Set[str]] = None):
        self.ordering_fields = ordering_fields

    def __call__(
        self,
        ordering: str = Query(
            "",
            description="Comma seperated list of ordering the results.\n"
            "You may also specify reverse orderings by prefixing the field name with '-'.",
            example="-name,created_at",
        ),
    ) -> OrderingQuery:
        orderings = list(filter(None, ordering.split(",")))
        if self.ordering_fields is not None:
            for x in orderings:
                name = x.startswith("-") and x[1:] or x
                if name not in self.ordering_fields:
                    raise BizError(
                        ErrorCode.IllegalFieldError,
                        f"{x} is not available in ordering fields",
                    )
        return OrderingQuery(orderings=orderings)


def parse_ordering_query(
    ordering_fields: Optional[List[str]] = None,
) -> Callable[..., OrderingQuery]:
    if ordering_fields is None:
        return OrderingQueryParser()
    else:
        return OrderingQueryParser(set(ordering_fields))


def parse_pagination_query(
    offset: NoneNegativeInt = Query(0),
    limit: PaginationLimit = Query(100),
) -> PaginationQuery:
    return PaginationQuery(offset=offset, limit=limit)
