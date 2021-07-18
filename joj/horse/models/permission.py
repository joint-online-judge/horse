from enum import Enum
from typing import Optional, Type, TypeVar

from tortoise import fields, models
from umongo import fields
from umongo.embedded_document import EmbeddedDocumentImplementation

from joj.horse.models.base import BaseORMModel

# from joj.horse.schemas.base import BaseModel
from joj.horse.utils.base import StrEnumMixin
from joj.horse.utils.db import instance

# BaseModelType = TypeVar("BaseModelType", bound=BaseModel)


class DefaultRole(StrEnumMixin, Enum):
    ROOT = "root"
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    JUDGE = "judge"


class ScopeType(StrEnumMixin, Enum):
    DOMAIN_GENERAL = "general"
    DOMAIN_PROBLEM = "problem"
    DOMAIN_PROBLEM_SET = "problem_set"
    DOMAIN_RECORD = "record"

    SITE_DOMAIN = "domain"
    SITE_USER = "user"

    UNKNOWN = "unknown"


class PermissionType(StrEnumMixin, Enum):
    view = "view"
    view_mod_badge = "view_mod_badge"
    view_hidden = "view_hidden"
    view_config = "view_config"
    view_config_self = "view_config_self"

    edit_permission = "edit_permission"
    edit = "edit"

    create = "create"
    submit = "submit"
    claim = "claim"
    scoreboard = "scoreboard"
    manage = "manage"
    detail = "detail"
    code = "code"
    rejudge = "rejudge"
    delete = "delete"

    unlimited_quota = "unlimited_quota"
    judge = "judge"

    unknown = "unknown"


T = TypeVar("T", bound=Type[EmbeddedDocumentImplementation])


def wrap_permission(scope: ScopeType, cls: T) -> T:
    value = "Wrapped" + cls.__name__
    names = []
    for k in cls().dump().keys():
        if not k.startswith("_"):
            perm = PermissionType[k]
            names.append((k, (scope, perm)))
    return Enum(value, names=names, type=tuple)  # type: ignore


@instance.register
class GeneralPermission(EmbeddedDocumentImplementation):
    view = fields.BooleanField(default=True)
    edit_permission = fields.BooleanField(default=False)
    view_mod_badge = fields.BooleanField(default=True)  # what's this?
    edit = fields.BooleanField(default=False)
    unlimited_quota = fields.BooleanField(default=False)


@instance.register
class ProblemPermission(EmbeddedDocumentImplementation):
    create = fields.BooleanField(default=False)
    view = fields.BooleanField(default=True)
    view_hidden = fields.BooleanField(default=False)
    submit = fields.BooleanField(default=True)

    edit = fields.BooleanField(default=False)
    view_config = fields.BooleanField(default=False)


@instance.register
class ProblemSetPermission(EmbeddedDocumentImplementation):
    create = fields.BooleanField(default=False)
    view = fields.BooleanField(default=True)
    view_hidden = fields.BooleanField(default=False)
    claim = fields.BooleanField(default=True)

    scoreboard = fields.BooleanField(default=False)
    manage = fields.BooleanField(default=False)

    edit = fields.BooleanField(default=False)
    view_config = fields.BooleanField(default=False)


@instance.register
class RecordPermission(EmbeddedDocumentImplementation):
    view = fields.BooleanField(default=True)
    detail = fields.BooleanField(default=False)
    code = fields.BooleanField(default=False)
    judge = fields.BooleanField(default=False)
    rejudge = fields.BooleanField(default=False)


@instance.register
class UserSpecificPermission(EmbeddedDocumentImplementation):
    view = fields.BooleanField(default=True)
    view_hidden = fields.BooleanField(default=False)


@instance.register
class DomainSpecificPermission(EmbeddedDocumentImplementation):
    create = fields.BooleanField(default=False)
    edit = fields.BooleanField(default=False)
    delete = fields.BooleanField(default=False)
    view_hidden = fields.BooleanField(default=False)


@instance.register
class DomainPermission(EmbeddedDocumentImplementation):
    """All permissions in a domain"""

    general = fields.EmbeddedField(GeneralPermission, default=GeneralPermission())
    problem = fields.EmbeddedField(ProblemPermission, default=ProblemPermission())
    problem_set = fields.EmbeddedField(
        ProblemSetPermission, default=ProblemSetPermission()
    )
    record = fields.EmbeddedField(RecordPermission, default=RecordPermission())


@instance.register
class SitePermission(DomainPermission):
    user = fields.EmbeddedField(
        UserSpecificPermission, default=UserSpecificPermission()
    )
    domain = fields.EmbeddedField(
        DomainSpecificPermission, default=DomainSpecificPermission()
    )


def __get_default_permission(
    model: Type[EmbeddedDocumentImplementation], value: Optional[bool]
) -> EmbeddedDocumentImplementation:
    obj = model()
    # breakpoint()
    if value is not None:
        for key in obj._fields:
            obj[key] = value
    return obj


def __get_default_domain_permission(value: Optional[bool] = None) -> DomainPermission:
    return DomainPermission(
        general=__get_default_permission(GeneralPermission, value),
        problem=__get_default_permission(ProblemPermission, value),
        problem_set=__get_default_permission(ProblemSetPermission, value),
        record=__get_default_permission(RecordPermission, value),
    )


def __get_default_site_permission(
    value1: Optional[bool] = None, value2: Optional[bool] = None
) -> SitePermission:
    return SitePermission(
        **__get_default_domain_permission(value1).dump(),
        user=__get_default_permission(UserSpecificPermission, value2),
        domain=__get_default_permission(DomainSpecificPermission, value2),
    )


FIXED_ROLES = {DefaultRole.JUDGE}
READONLY_ROLES = {DefaultRole.ROOT, DefaultRole.GUEST, DefaultRole.JUDGE}

DEFAULT_DOMAIN_PERMISSION = {
    DefaultRole.ROOT: __get_default_domain_permission(True),
    DefaultRole.ADMIN: __get_default_domain_permission(True),
    DefaultRole.USER: __get_default_domain_permission(None),
    DefaultRole.GUEST: __get_default_domain_permission(False),
}

# set permission for judge
__DEFAULT_JUDGE_PERMISSION = __get_default_site_permission(False, False)
__DEFAULT_JUDGE_PERMISSION.record.code = True
__DEFAULT_JUDGE_PERMISSION.record.judge = True
__DEFAULT_JUDGE_PERMISSION.problem.view_config = True
__DEFAULT_JUDGE_PERMISSION.problem_set.view_config = True

DEFAULT_SITE_PERMISSION = {
    DefaultRole.ROOT: __get_default_site_permission(True, True),
    DefaultRole.ADMIN: __get_default_site_permission(None, True),
    DefaultRole.USER: __get_default_site_permission(False, None),
    DefaultRole.GUEST: __get_default_site_permission(False, False),
    DefaultRole.JUDGE: __DEFAULT_JUDGE_PERMISSION,
}


class Permission:
    DomainGeneral = wrap_permission(ScopeType.DOMAIN_GENERAL, GeneralPermission)
    DomainProblem = wrap_permission(ScopeType.DOMAIN_PROBLEM, ProblemPermission)
    DomainProblemSet = wrap_permission(
        ScopeType.DOMAIN_PROBLEM_SET, ProblemSetPermission
    )
    DomainRecord = wrap_permission(ScopeType.DOMAIN_RECORD, RecordPermission)

    SiteUser = wrap_permission(ScopeType.SITE_USER, UserSpecificPermission)
    SiteDomain = wrap_permission(ScopeType.SITE_DOMAIN, DomainSpecificPermission)
