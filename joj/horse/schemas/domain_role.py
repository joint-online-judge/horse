from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import Field, validator
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
    permission: Dict[str, Any] = {}
    updated_at: datetime = datetime.utcnow()

    # @validator("permission", pre=True, always=True)
    # def default_permission(
    #     cls, v: Any, *, values: Any, **kwargs: Any
    # ) -> Dict[str, Any]:
    #     return v or DomainPermission().dump()

    @validator("updated_at", pre=True, always=True)
    def default_updated_at(cls, v: datetime, *, values: Any, **kwargs: Any) -> datetime:
        return v or datetime.utcnow()


# class DomainRole(DomainRoleCreate, BaseODMSchema):
#     domain: ReferenceSchema[Domain]
#     role: str
#
#     _validator_domain: Callable[
#         [AnyCallable], classmethod
#     ] = reference_schema_validator("domain", Domain)
#
#     _validator_permission: Callable[
#         [AnyCallable], classmethod
#     ] = embedded_dict_schema_validator("permission")
#
#


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
