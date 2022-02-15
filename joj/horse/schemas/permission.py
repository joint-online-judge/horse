from typing import Dict, List, Literal, NamedTuple, Type, TypeVar

from pydantic import validator

from joj.horse.models.permission import (
    DefaultRole as DefaultRole,
    PermissionType as PermissionType,
    ScopeType as ScopeType,
)
from joj.horse.schemas.base import BaseModel


class PermissionBase(BaseModel):
    @classmethod
    def get_default(
        cls: Type["PermissionBase"], value: bool | None = None
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
    view: bool = False
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
        cls: Type["DomainPermission"], value: bool | None = None
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
        value1: bool | None = None,
        value2: bool | None = None,
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
__DEFAULT_JUDGE_PERMISSION.record.judge = True


DEFAULT_SITE_PERMISSION = {
    DefaultRole.ROOT: SitePermission.get_default_site_permission(True, True),
    DefaultRole.ADMIN: SitePermission.get_default_site_permission(None, True),
    DefaultRole.USER: SitePermission.get_default_site_permission(False, None),
    DefaultRole.GUEST: SitePermission.get_default_site_permission(False, False),
    DefaultRole.JUDGE: __DEFAULT_JUDGE_PERMISSION,
}


class PermKey(NamedTuple):
    scope: ScopeType
    permission: PermissionType


class PermCompose(BaseModel):
    permissions: List["PermCompose" | PermKey]
    action: Literal["AND", "OR"] = "AND"

    @validator("permissions")
    def validate_permissions(
        cls, v: List["PermCompose" | PermKey]
    ) -> List["PermCompose" | PermKey]:
        if len(v) == 0:
            raise ValueError("permissions can't be empty list")
        return v

    def is_action_and(self) -> bool:
        return len(self.permissions) == 1 or self.action == "AND"

    def is_action_or(self) -> bool:
        return len(self.permissions) == 1 or self.action == "OR"

    def __or__(self, other: "PermCompose") -> "PermCompose":
        if self.is_action_or() and other.is_action_or():
            permissions = self.permissions + other.permissions
        else:
            permissions = [self.copy(), other.copy()]
        return PermCompose(permissions=permissions, action="OR")

    def __and__(self, other: "PermCompose") -> "PermCompose":
        if self.is_action_and() and other.is_action_and():
            permissions = self.permissions + other.permissions
        else:
            permissions = [self.copy(), other.copy()]
        return PermCompose(permissions=permissions, action="AND")


PermCompose.update_forward_refs()


T = TypeVar("T", bound=PermissionBase)


def wrap_permission(scope: ScopeType, cls: Type[T]) -> T:
    value = "Wrapped" + cls.__name__
    names = {}
    for k in cls.__fields__.keys():
        if not k.startswith("_"):
            perm = PermCompose(
                permissions=[PermKey(scope=scope, permission=PermissionType[k])]
            )
            names[k] = perm
    return type(value, (object,), names)  # type: ignore


class Permission:
    DomainGeneral = wrap_permission(ScopeType.DOMAIN_GENERAL, GeneralPermission)
    DomainProblem = wrap_permission(ScopeType.DOMAIN_PROBLEM, ProblemPermission)
    DomainProblemSet = wrap_permission(
        ScopeType.DOMAIN_PROBLEM_SET, ProblemSetPermission
    )
    DomainRecord = wrap_permission(ScopeType.DOMAIN_RECORD, RecordPermission)

    SiteUser = wrap_permission(ScopeType.SITE_USER, UserSpecificPermission)
    SiteDomain = wrap_permission(ScopeType.SITE_DOMAIN, DomainSpecificPermission)
