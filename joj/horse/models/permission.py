from enum import Enum
from typing import Optional, Type, TypeVar

from pydantic import BaseModel
from umongo import fields
from umongo.embedded_document import EmbeddedDocumentImplementation

from joj.horse.utils.db import instance

BaseModelType = TypeVar('BaseModelType', bound=BaseModel)


class DefaultRole(str, Enum):
    ROOT = "root"
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    JUDGE = "judge"


class ScopeType(str, Enum):
    GENERAL = "general"
    PROBLEM = "problem"
    PROBLEM_SET = "problem_set"
    RECORD = "record"
    UNKNOWN = "unknown"

    DOMAIN = "domain"
    USER = "user"


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


@instance.register
class GeneralPermission(EmbeddedDocumentImplementation):
    view = fields.BoolField(default=True)
    edit_permission = fields.BoolField(default=False)
    view_mod_badge = fields.BoolField(default=True)  # what's this?
    edit_description = fields.BoolField(default=False)
    unlimited_quota = fields.BoolField(default=False)


# class GeneralPermission(BaseModel):
#     view: bool = True
#     edit_permission: bool = False
#     view_mod_badge: bool = True  # what's this?
#     edit_description: bool = False
#     unlimited_quota: bool = False

@instance.register
class ProblemPermission(EmbeddedDocumentImplementation):
    create = fields.BoolField(default=False)
    view = fields.BoolField(default=True)
    view_hidden = fields.BoolField(default=False)
    submit = fields.BoolField(default=True)

    edit_config = fields.BoolField(default=False)
    edit_config_self = fields.BoolField(default=True)
    view_config = fields.BoolField(default=False)
    view_config_self = fields.BoolField(default=True)


# class ProblemPermission(BaseModel):
#     create: bool = False
#     view: bool = True
#     view_hidden: bool = False
#     submit: bool = True
#
#     edit_config: bool = False
#     edit_config_self: bool = True
#     view_config: bool = False
#     view_config_self: bool = True

@instance.register
class ProblemSetPermission(EmbeddedDocumentImplementation):
    create = fields.BoolField(default=False)
    view = fields.BoolField(default=True)
    view_hidden = fields.BoolField(default=False)
    claim = fields.BoolField(default=True)

    scoreboard = fields.BoolField(default=False)
    manage = fields.BoolField(default=False)

    edit_config = fields.BoolField(default=False)
    edit_config_self = fields.BoolField(default=True)
    view_config = fields.BoolField(default=False)
    view_config_self = fields.BoolField(default=True)


# class ProblemSetPermission(BaseModel):
#     create: bool = False
#     view: bool = True
#     view_hidden: bool = False
#     claim: bool = True
#
#     scoreboard: bool = False
#     manage: bool = False
#
#     edit_config: bool = False
#     edit_config_self: bool = True
#     view_config: bool = False
#     view_config_self: bool = True


@instance.register
class RecordPermission(EmbeddedDocumentImplementation):
    view = fields.BoolField(default=True)
    detail = fields.BoolField(default=False)
    code = fields.BoolField(default=False)
    judge = fields.BoolField(default=False)
    rejudge = fields.BoolField(default=False)


# class RecordPermission(BaseModel):
#     view: bool = True
#     detail: bool = False
#     code: bool = False
#     judge: bool = False
#     rejudge: bool = False

@instance.register
class DomainPermission(EmbeddedDocumentImplementation):
    """All permissions in a domain"""

    general = fields.EmbeddedField(GeneralPermission, default=GeneralPermission())
    problem = fields.EmbeddedField(ProblemPermission, default=ProblemPermission())
    problem_set = fields.EmbeddedField(ProblemSetPermission, default=ProblemSetPermission())
    record = fields.EmbeddedField(RecordPermission, default=RecordPermission())


# class DomainPermission(BaseModel):
#     """All permissions in a domain"""
#
#     general: GeneralPermission = GeneralPermission()
#     problem: ProblemPermission = ProblemPermission()
#     problem_set: ProblemSetPermission = ProblemSetPermission()
#     record: RecordPermission = RecordPermission()


@instance.register
class UserSpecificPermission(EmbeddedDocumentImplementation):
    view = fields.BoolField(default=True)
    view_hidden = fields.BoolField(default=False)


@instance.register
class DomainSpecificPermission(EmbeddedDocumentImplementation):
    create = fields.BoolField(default=False)
    edit = fields.BoolField(default=False)
    view_hidden = fields.BoolField(default=False)


# class UserSpecificPermission(BaseModel):
#     view: bool = True
#     view_hidden: bool = False
#
#
# class DomainSpecificPermission(BaseModel):
#     create: bool = False
#     edit: bool = False
#     view_hidden: bool = False


@instance.register
class SitePermission(DomainPermission):
    user = fields.EmbeddedField(UserSpecificPermission, default=UserSpecificPermission())
    domain = fields.EmbeddedField(DomainSpecificPermission, default=DomainSpecificPermission())
    # domain: DomainSpecificPermission = DomainSpecificPermission()
    # user: UserSpecificPermission = UserSpecificPermission()
    pass


def __get_default_permission(model: Type[EmbeddedDocumentImplementation],
                             value: Optional[bool]) -> EmbeddedDocumentImplementation:
    obj = model()
    # breakpoint()
    if value is not None:
        for key in obj._fields:
            obj[key] = value
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
        **__get_default_domain_permission(value1).dump(),
        user=__get_default_permission(UserSpecificPermission, value2),
        domain=__get_default_permission(DomainSpecificPermission, value2),
    )


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
