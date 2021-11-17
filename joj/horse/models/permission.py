from enum import Enum

from joj.horse.utils.base import StrEnumMixin


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
    view_list = "view_list"
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


FIXED_ROLES = {DefaultRole.JUDGE}
READONLY_ROLES = {DefaultRole.ROOT, DefaultRole.GUEST, DefaultRole.JUDGE}
