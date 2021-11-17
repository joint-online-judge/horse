from enum import Enum
from typing import Dict, Optional, Type, TypeVar

from joj.horse.models.permission import (
    DefaultRole as DefaultRole,
    PermissionType as PermissionType,
    ScopeType as ScopeType,
)
from joj.horse.schemas.base import BaseModel


class PermissionBase(BaseModel):
    @classmethod
    def get_default(
        cls: Type["PermissionBase"], value: Optional[bool] = None
    ) -> "PermissionBase":
        obj = cls()
        if value is not None:
            for key in obj.__dict__:
                obj.__dict__[key] = value
        return obj


class GeneralPermission(PermissionBase):
    view: bool = True
    edit_permission: bool = False
    view_mod_badge: bool = True  # what's this?
    edit: bool = False
    unlimited_quota: bool = False


class ProblemPermission(PermissionBase):
    create: bool = False
    view: bool = True
    view_hidden: bool = False
    submit: bool = True

    edit: bool = False
    view_config: bool = False


class ProblemSetPermission(PermissionBase):
    create: bool = False
    view: bool = True
    view_hidden: bool = False
    claim: bool = True

    scoreboard: bool = False
    manage: bool = False

    edit: bool = False
    view_config: bool = False


class RecordPermission(PermissionBase):
    view: bool = True
    detail: bool = False
    code: bool = False
    judge: bool = False
    rejudge: bool = False


class UserSpecificPermission(PermissionBase):
    view: bool = True
    view_hidden: bool = False
    view_list: bool = False


class DomainSpecificPermission(PermissionBase):
    create: bool = False
    edit: bool = False
    delete: bool = False
    view_hidden: bool = False


class DomainPermission(BaseModel):
    """All permissions in a domain"""

    general: GeneralPermission = GeneralPermission()
    problem: ProblemPermission = ProblemPermission()
    problem_set: ProblemSetPermission = ProblemSetPermission()
    record: RecordPermission = RecordPermission()

    @classmethod
    def get_default(
        cls: Type["DomainPermission"], value: Optional[bool] = None
    ) -> "DomainPermission":
        return DomainPermission(
            general=GeneralPermission.get_default(value),
            problem=ProblemPermission.get_default(value),
            problem_set=ProblemSetPermission.get_default(value),
            record=RecordPermission.get_default(value),
        )


class SitePermission(DomainPermission):
    user: UserSpecificPermission = UserSpecificPermission()
    domain: DomainSpecificPermission = DomainSpecificPermission()

    @classmethod
    def get_default_site_permission(
        cls: Type["SitePermission"],
        value1: Optional[bool] = None,
        value2: Optional[bool] = None,
    ) -> "SitePermission":
        return SitePermission(
            **DomainPermission.get_default(value1).dict(),
            user=UserSpecificPermission.get_default(value2),
            domain=DomainSpecificPermission.get_default(value2),
        )


DEFAULT_DOMAIN_PERMISSION: Dict[str, DomainPermission] = {
    DefaultRole.ROOT: DomainPermission.get_default(True),
    DefaultRole.ADMIN: DomainPermission.get_default(True),
    DefaultRole.USER: DomainPermission.get_default(None),
    DefaultRole.GUEST: DomainPermission.get_default(False),
}

# set permission for judge
__DEFAULT_JUDGE_PERMISSION = SitePermission.get_default_site_permission(False, False)
__DEFAULT_JUDGE_PERMISSION.record.code = True
__DEFAULT_JUDGE_PERMISSION.record.judge = True
__DEFAULT_JUDGE_PERMISSION.problem.view_config = True
__DEFAULT_JUDGE_PERMISSION.problem_set.view_config = True

DEFAULT_SITE_PERMISSION = {
    DefaultRole.ROOT: SitePermission.get_default_site_permission(True, True),
    DefaultRole.ADMIN: SitePermission.get_default_site_permission(None, True),
    DefaultRole.USER: SitePermission.get_default_site_permission(False, None),
    DefaultRole.GUEST: SitePermission.get_default_site_permission(False, False),
    DefaultRole.JUDGE: __DEFAULT_JUDGE_PERMISSION,
}


T = TypeVar("T", bound=Type[PermissionBase])


def wrap_permission(scope: ScopeType, cls: T) -> T:
    value = "Wrapped" + cls.__name__
    names = []
    for k in cls.__fields__.keys():
        if not k.startswith("_"):
            perm = PermissionType[k]
            names.append((k, (scope, perm)))
    return Enum(value, names=names, type=tuple)  # type: ignore


class Permission:
    DomainGeneral = wrap_permission(ScopeType.DOMAIN_GENERAL, GeneralPermission)
    DomainProblem = wrap_permission(ScopeType.DOMAIN_PROBLEM, ProblemPermission)
    DomainProblemSet = wrap_permission(
        ScopeType.DOMAIN_PROBLEM_SET, ProblemSetPermission
    )
    DomainRecord = wrap_permission(ScopeType.DOMAIN_RECORD, RecordPermission)

    SiteUser = wrap_permission(ScopeType.SITE_USER, UserSpecificPermission)
    SiteDomain = wrap_permission(ScopeType.SITE_DOMAIN, DomainSpecificPermission)
