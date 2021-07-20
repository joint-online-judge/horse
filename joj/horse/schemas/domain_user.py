from typing import List, Optional

from pydantic import Field
from tortoise.contrib.pydantic import pydantic_model_creator

from joj.horse.models.base import init_models
from joj.horse.models.domain_user import DomainUser as DomainUserModel
from joj.horse.models.permission import DefaultRole
from joj.horse.schemas import BaseModel
from joj.horse.schemas.domain import Domain
from joj.horse.schemas.permission import DomainPermission
from joj.horse.schemas.user import UserBase

# from joj.horse.schemas.domain_role import DomainPermission

init_models()
DomainUser = pydantic_model_creator(
    DomainUserModel,
    name="DomainUser",
    exclude=("domain", "user"),
)
DomainUserGenerated = pydantic_model_creator(DomainUserModel, name="DomainUserFull")


class DomainUserExpanded(DomainUserGenerated):  # type: ignore
    domain: Optional[Domain] = None
    user: Optional[UserBase] = None


# class DomainUser(BaseODMSchema):
#     domain: ReferenceSchema[Domain]
#     user: ReferenceSchema[UserBase]
#     role: str
#
#     join_at: Optional[datetime] = None
#
#     @validator("join_at", pre=True, always=True)
#     def default_join_at(cls, v: datetime, *, values: Any, **kwargs: Any) -> datetime:
#         return v or datetime.utcnow()
#
#     _validator_domain: Callable[
#         [AnyCallable], classmethod
#     ] = reference_schema_validator("domain", Domain)
#     _validator_user: Callable[[AnyCallable], classmethod] = reference_schema_validator(
#         "user", UserBase
#     )
#


class DomainUserPermission(DomainUser):  # type: ignore
    class Config:
        title = "DomainUserPermission"

    permission: DomainPermission


class ListDomainUsers(BaseModel):
    results: List[DomainUser]  # type: ignore


class DomainUserAdd(BaseModel):
    role: DefaultRole = Field(DefaultRole.USER)
    user: str = Field(..., description="'me' or ObjectId of the user")
