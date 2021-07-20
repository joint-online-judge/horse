from typing import Any, Dict, List, Optional

from pydantic import Field
from tortoise.contrib.pydantic import pydantic_model_creator

from joj.horse.models.base import init_models
from joj.horse.models.domain_role import DomainRole as DomainRoleModel

# from joj.horse.models.permission import DomainPermission
from joj.horse.schemas import BaseModel
from joj.horse.schemas.base import NoneEmptyLongStr
from joj.horse.schemas.permission import DomainPermission


class DomainRoleEdit(BaseModel):
    role: Optional[NoneEmptyLongStr] = Field(None, description="New role name")
    permission: Optional[Dict[str, Any]] = Field(
        None, description="The permission which needs to be updated"
    )


class DomainRoleCreate(BaseModel):
    role: NoneEmptyLongStr
    permission: DomainPermission = DomainPermission()


init_models()
DomainRoleGenerated = pydantic_model_creator(
    DomainRoleModel,
    name="DomainRole",
    exclude=("domain",),
)


class DomainRole(DomainRoleGenerated):  # type: ignore
    permission: DomainPermission


class ListDomainRoles(BaseModel):
    results: List[DomainRole]
