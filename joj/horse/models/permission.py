from typing import Type, Optional
from enum import Enum
from pydantic import BaseModel


class DefaultRole(str, Enum):
    ROOT = "root"
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"


class ScopeType(str, Enum):
    GENERAL = "general"
    PROBLEM = "problem"
    PROBLEM_SET = "problem_set"
    RECORD = "record"
    UNKNOWN = "unknown"


class PermissionType(str, Enum):
    VIEW = "view"
    VIEW_MOD_BADGE = "view_mod_badge"
    VIEW_HIDDEN = "view_hidden"
    VIEW_CONFIG = "view_config"
    VIEW_CONFIG_SELF = "view_config_self"

    EDIT_PERMISSION = "edit_permission"
    EDIT_DESCRIPTION = "edit_description"
    EDIT_CONFIG = "edit_config"
    EDIT_CONFIG_SELF = "edit_config_self"

    CREATE = "create"
    SUBMIT = "submit"
    CLAIM = "claim"
    SCOREBOARD = "scoreboard"
    MANAGE = "manage"
    DETAIL = "detail"
    CODE = "code"
    REJUDGE = "rejudge"

    UNKNOWN = "unknown"


class GeneralPermission(BaseModel):
    view: bool = True
    edit_permission: bool = False
    view_mod_badge: bool = True  # what's this?
    edit_description: bool = False
    unlimited_quota: bool = False


class ProblemPermission(BaseModel):
    create: bool = False
    view: bool = True
    view_hidden: bool = False
    submit: bool = True

    edit_config: bool = False
    edit_config_self: bool = True
    view_config: bool = False
    view_config_self: bool = True


class ProblemSetPermission(BaseModel):
    create: bool = False
    view: bool = True
    view_hidden: bool = False
    claim: bool = True

    scoreboard: bool = False
    manage: bool = False

    edit_config: bool = False
    edit_config_self: bool = True
    view_config: bool = False
    view_config_self: bool = True


class RecordPermission(BaseModel):
    view: bool = False
    detail: bool = False
    code: bool = False
    rejudge: bool = False


class DomainPermission(BaseModel):
    """All permissions in a domain"""

    general: GeneralPermission = GeneralPermission()
    problem: ProblemPermission = ProblemPermission()
    problem_set: ProblemSetPermission = ProblemSetPermission()
    record: RecordPermission = RecordPermission()


class UserSpecificPermission(BaseModel):
    view: bool = True
    view_hidden: bool = False


class DomainSpecificPermission(BaseModel):
    create: bool = False
    edit: bool = False
    view_hidden: bool = False


class SitePermission(DomainPermission):
    domain: DomainSpecificPermission = DomainSpecificPermission()
    user: UserSpecificPermission = UserSpecificPermission()


def __get_default_permission(model: Type[BaseModel], value: Optional[bool]):
    obj = model()
    if value is not None:
        for key in obj.__fields_set__:
            obj.__fields__[key] = value
    return obj


def __get_default_domain_permission(value: Optional[bool] = None):
    return DomainPermission(
        general=__get_default_permission(GeneralPermission, value),
        problem=__get_default_permission(ProblemPermission, value),
        problem_set=__get_default_permission(ProblemSetPermission, value),
        record=__get_default_permission(RecordPermission, value),
    )


def __get_default_site_permission(value1: Optional[bool] = None, value2: Optional[bool] = None):
    return SitePermission(
        **__get_default_domain_permission(value1).dict(),
        user=__get_default_permission(GeneralPermission, value2),
        domain=__get_default_permission(ProblemPermission, value2),
    )


DEFAULT_DOMAIN_PERMISSION = {
    DefaultRole.ROOT: __get_default_domain_permission(True),
    DefaultRole.ADMIN: __get_default_domain_permission(True),
    DefaultRole.USER: __get_default_domain_permission(None),
    DefaultRole.GUEST: __get_default_domain_permission(False),
}

DEFAULT_SITE_PERMISSION = {
    DefaultRole.ROOT: __get_default_site_permission(True, True),
    DefaultRole.ADMIN: __get_default_site_permission(None, True),
    DefaultRole.USER: __get_default_site_permission(False, None),
    DefaultRole.GUEST: __get_default_site_permission(False, False),
}
