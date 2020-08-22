from pydantic import BaseModel


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
