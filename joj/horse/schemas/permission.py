from joj.horse.models.permission import DefaultRole, PermissionType, ScopeType
from joj.horse.schemas.base import BaseModel


class GeneralPermission(BaseModel):
    view: bool = True
    edit_permission: bool = False
    view_mod_badge: bool = True  # what's this?
    edit: bool = False
    unlimited_quota: bool = False


class ProblemPermission(BaseModel):
    create: bool = False
    view: bool = True
    view_hidden: bool = False
    submit: bool = True

    edit: bool = False
    view_config: bool = False


class ProblemSetPermission(BaseModel):
    create: bool = False
    view: bool = True
    view_hidden: bool = False
    claim: bool = True

    scoreboard: bool = False
    manage: bool = False

    edit: bool = False
    view_config: bool = False


class RecordPermission(BaseModel):
    view: bool = True
    detail: bool = False
    code: bool = False
    judge: bool = False
    rejudge: bool = False


class UserSpecificPermission(BaseModel):
    view: bool = True
    view_hidden: bool = False


class DomainSpecificPermission(BaseModel):
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


class SitePermission(DomainPermission):
    user: UserSpecificPermission = UserSpecificPermission()
    domain: DomainSpecificPermission = DomainSpecificPermission()
