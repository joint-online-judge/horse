from enum import Enum
from typing import Optional, Type, TypeVar

from pydantic import BaseModel
from umongo import fields
from umongo.embedded_document import EmbeddedDocumentImplementation

from joj.horse.utils.db import instance

BaseModelType = TypeVar("BaseModelType", bound=BaseModel)


class DefaultRole(str, Enum):
    ROOT = "root"
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    JUDGE = "judge"


class ScopeType(str, Enum):
    DOMAIN_GENERAL = "general"
    DOMAIN_PROBLEM = "problem"
    DOMAIN_PROBLEM_SET = "problem_set"
    DOMAIN_RECORD = "record"

    SITE_DOMAIN = "domain"
    SITE_USER = "user"

    UNKNOWN = "unknown"


class PermissionType(str, Enum):
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


T = TypeVar("T")


def wrap_permission(scope: ScopeType, cls: T) -> T:
    value = "Wrapped" + cls.__name__  # type: ignore
    names = []
    for k, v in cls.__dict__.items():
        if not k.startswith("_"):
            perm = PermissionType[k]
            names.append((k, (scope, perm)))
    return Enum(value, names=names, type=tuple)  # type: ignore


class GeneralPermissionModel:
    view = fields.BoolField(default=True)
    edit_permission = fields.BoolField(default=False)
    view_mod_badge = fields.BoolField(default=True)  # what's this?
    edit = fields.BoolField(default=False)
    unlimited_quota = fields.BoolField(default=False)


@instance.register
class GeneralPermission(GeneralPermissionModel, EmbeddedDocumentImplementation):
    pass


class ProblemPermissionModel:
    create = fields.BoolField(default=False)
    view = fields.BoolField(default=True)
    view_hidden = fields.BoolField(default=False)
    submit = fields.BoolField(default=True)

    edit = fields.BoolField(default=False)
    view_config = fields.BoolField(default=False)


@instance.register
class ProblemPermission(ProblemPermissionModel, EmbeddedDocumentImplementation):
    pass


class ProblemSetPermissionModel:
    create = fields.BoolField(default=False)
    view = fields.BoolField(default=True)
    view_hidden = fields.BoolField(default=False)
    claim = fields.BoolField(default=True)

    scoreboard = fields.BoolField(default=False)
    manage = fields.BoolField(default=False)

    edit = fields.BoolField(default=False)
    view_config = fields.BoolField(default=False)


@instance.register
class ProblemSetPermission(ProblemSetPermissionModel, EmbeddedDocumentImplementation):
    pass


class RecordPermissionModel:
    view = fields.BoolField(default=True)
    detail = fields.BoolField(default=False)
    code = fields.BoolField(default=False)
    judge = fields.BoolField(default=False)
    rejudge = fields.BoolField(default=False)


@instance.register
class RecordPermission(RecordPermissionModel, EmbeddedDocumentImplementation):
    pass


class UserSpecificPermissionModel:
    view = fields.BoolField(default=True)
    view_hidden = fields.BoolField(default=False)


@instance.register
class UserSpecificPermission(
    UserSpecificPermissionModel, EmbeddedDocumentImplementation
):
    pass


class DomainSpecificPermissionModel:
    create = fields.BoolField(default=False)
    edit = fields.BoolField(default=False)
    delete = fields.BoolField(default=False)
    view_hidden = fields.BoolField(default=False)


@instance.register
class DomainSpecificPermission(
    DomainSpecificPermissionModel, EmbeddedDocumentImplementation
):
    pass


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
    DomainGeneral = wrap_permission(ScopeType.DOMAIN_GENERAL, GeneralPermissionModel)
    DomainProblem = wrap_permission(ScopeType.DOMAIN_PROBLEM, ProblemPermissionModel)
    DomainProblemSet = wrap_permission(
        ScopeType.DOMAIN_PROBLEM_SET, ProblemSetPermissionModel
    )
    DomainRecord = wrap_permission(ScopeType.DOMAIN_RECORD, RecordPermissionModel)

    SiteUser = wrap_permission(ScopeType.SITE_USER, UserSpecificPermissionModel)
    SiteDomain = wrap_permission(ScopeType.SITE_DOMAIN, DomainSpecificPermissionModel)
