from enum import Enum, auto
from pydantic import BaseModel


class ScopeType(Enum):
    GENERAL = "general"
    PROBLEM = "problem"
    PROBLEM_SET = "problem_set"
    RECORD = "record"
    UNKNOWN = "unknown"


class PermissionType(Enum):
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
    view: bool = False
    edit_permission: bool = False
    view_mod_badge: bool = True  # what's this?
    edit_description: bool = False


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


class Permission(BaseModel):
    """All permissions in a domain"""

    general: GeneralPermission = GeneralPermission()
    problem: ProblemPermission = ProblemPermission()
    problem_set: ProblemSetPermission = ProblemSetPermission()
    record: RecordPermission = RecordPermission()
