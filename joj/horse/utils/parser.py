from datetime import datetime
from functools import lru_cache
from typing import Any, Callable, Coroutine, List, Optional, Type

from fastapi import Depends, Path, Query, Request
from pydantic.fields import Undefined
from sqlalchemy.orm import subqueryload

from joj.horse import models, schemas
from joj.horse.models.permission import PermissionType, ScopeType
from joj.horse.schemas.base import (
    BT,
    NoneEmptyLongStr,
    NoneNegativeInt,
    PaginationLimit,
)
from joj.horse.schemas.query import OrderingQuery, PaginationQuery
from joj.horse.utils.auth import Authentication, DomainAuthentication, get_domain
from joj.horse.utils.errors import BizError, ErrorCode


async def parse_uid(
    uid: str = Query("me", description="'me' or id of the user"),
    auth: Authentication = Depends(),
) -> models.User:
    if uid == "me":
        return parse_user_from_auth(auth)
    user = await models.User.get_or_none(id=uid)
    if user:
        return user
    raise BizError(ErrorCode.UserNotFoundError)


async def parse_uid_or_none(
    uid: Optional[str] = Query("", description="user id or 'me' or empty"),
    auth: Authentication = Depends(),
) -> Optional[models.User]:
    return await parse_uid(uid, auth) if uid else None


async def parse_user_from_path_or_query(
    user: str = Path("me", description="user id or 'me' or empty"),
    auth: Authentication = Depends(),
) -> models.User:
    return await parse_uid(user, auth)


def parse_user_from_auth(
    auth: Authentication = Depends(Authentication),
) -> models.User:
    if auth.jwt.category != "user":
        raise BizError(ErrorCode.UserNotFoundError)
    return models.User(
        id=auth.jwt.id,
        username=auth.jwt.username,
        email=auth.jwt.email,
        student_id=auth.jwt.student_id,
        real_name=auth.jwt.real_name,
        role=auth.jwt.role,
        is_active=auth.jwt.is_active,
    )


async def parse_domain_without_validation(
    domain: models.Domain = Depends(get_domain),
) -> models.Domain:
    return domain


async def parse_domain_from_auth(
    domain_auth: DomainAuthentication = Depends(),
) -> models.Domain:
    domain = domain_auth.auth.domain
    if (
        domain.hidden
        and domain_auth.auth.domain_user is None
        and not domain_auth.auth.check(
            ScopeType.SITE_DOMAIN, PermissionType.view_hidden
        )
    ):
        raise BizError(ErrorCode.DomainNotFoundError)
    return domain_auth.auth.domain


async def parse_domain_role(
    role: NoneEmptyLongStr = Path(..., description="name of the domain role"),
    domain: models.Domain = Depends(parse_domain_from_auth),
) -> models.DomainRole:
    domain_role_model = await models.DomainRole.get_or_none(
        domain_id=domain.id, role=role
    )
    if domain_role_model is None:
        raise BizError(ErrorCode.DomainRoleNotFoundError)
    return domain_role_model


async def parse_domain_invitation(
    invitation: str = Path(..., description="url or id of the domain invitation"),
    domain: models.Domain = Depends(parse_domain_from_auth),
) -> models.DomainInvitation:
    invitation_model = await models.DomainInvitation.find_by_domain_url_or_id(
        domain, invitation
    )
    if invitation_model:
        return invitation_model
    raise BizError(ErrorCode.DomainInvitationBadRequestError)


async def parse_problem(
    problem: str = Path(..., description="url or id of the problem"),
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
    problems: List[str], domain_auth: DomainAuthentication = Depends()
) -> List[models.Problem]:
    return [await parse_problem(oid, domain_auth) for oid in problems]


@lru_cache
def parse_problem_set_factory(
    load_problems: bool = False,
    load_links: bool = False,
) -> Callable[..., Coroutine[Any, Any, models.ProblemSet]]:
    options = []
    if load_problems:
        options.append(subqueryload(models.ProblemSet.problems))
    if load_links:
        options.append(
            subqueryload(models.ProblemSet.problem_problem_set_links).joinedload(
                models.ProblemProblemSetLink.problem
            )
        )

    async def wrapped(
        problem_set: str = Path(..., description="url or id of the problem set"),
        domain: models.Domain = Depends(parse_domain_from_auth),
    ) -> models.ProblemSet:
        problem_set_model = await models.ProblemSet.find_by_domain_url_or_id(
            domain, problem_set, options
        )
        if problem_set_model:
            return problem_set_model
        raise BizError(ErrorCode.ProblemSetNotFoundError)

    return wrapped


parse_problem_set = parse_problem_set_factory()


async def parse_problem_set_with_time(
    problem_set: str = Path(..., description="url or id of the problem set"),
    domain: models.Domain = Depends(parse_domain_from_auth),
) -> models.ProblemSet:
    # TODO: domain admin can see problem sets which are not in available period
    problem_set_model = await parse_problem_set(problem_set, domain)
    if datetime.utcnow() < problem_set_model.available_time:
        raise BizError(ErrorCode.ProblemSetBeforeAvailableError)
    if datetime.utcnow() > problem_set_model.due_time:
        raise BizError(ErrorCode.ProblemSetAfterDueError)
    return problem_set_model


async def parse_problem_group(problem_group: str) -> models.ProblemSet:
    problem_group_model = await models.ProblemGroup.find_by_id(problem_group)
    if problem_group_model:
        return problem_group_model
    raise BizError(ErrorCode.ProblemGroupNotFoundError)


async def parse_record(record: str, auth: Authentication = Depends()) -> schemas.Record:
    record_model = await schemas.Record.find_by_id(record)
    if record_model and record_model.user == auth.user:
        return record_model
    raise BizError(ErrorCode.RecordNotFoundError)


async def parse_record_judger(
    record: str, auth: Authentication = Depends()
) -> schemas.Record:
    record_model = await schemas.Record.find_by_id(record)
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


def parse_ordering_query(
    ordering_fields: Optional[List[str]] = None,
) -> Callable[..., OrderingQuery]:
    description = (
        "Comma seperated list of ordering the results.\n"
        "You may specify reverse orderings by prefixing the field name with '-'.\n\n"
    )
    if ordering_fields is None:
        ordering_fields = list()
    if len(ordering_fields) > 0:
        description += "Available fields: " + ",".join(ordering_fields)
    else:
        description += "Available fields: Any"
    ordering_fields_set = set(ordering_fields)

    def wrapped(
        ordering: str = Query(
            "",
            description=description,
        )
    ) -> OrderingQuery:
        orderings = list(filter(None, ordering.split(",")))
        if ordering_fields_set is not None:
            for x in orderings:
                name = x.startswith("-") and x[1:] or x
                if name not in ordering_fields_set:
                    raise BizError(
                        ErrorCode.IllegalFieldError,
                        f"{x} is not available in ordering fields",
                    )
        return OrderingQuery(orderings=orderings)

    return wrapped


def parse_pagination_query(
    offset: NoneNegativeInt = Query(0),
    limit: PaginationLimit = Query(100),
) -> PaginationQuery:
    return PaginationQuery(offset=offset, limit=limit)


def parse_edit_schema(
    cls: Type[BT],
) -> Callable[..., Coroutine[Any, Any, BT]]:
    async def wrapped(request: Request, edit: cls) -> BT:  # type: ignore[valid-type]
        data = await request.json()
        for field in cls.__fields__.values():
            if field.name not in data and field.alias not in data:
                setattr(edit, field.name, Undefined)
        return edit

    return wrapped
