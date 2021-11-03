from pydantic import Field

from joj.horse.models.permission import DefaultRole
from joj.horse.schemas import BaseModel

# from joj.horse.schemas.domain_role import DomainPermission


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


class DomainUserAdd(BaseModel):
    role: DefaultRole = Field(DefaultRole.USER)
    user: str = Field(..., description="'me' or id of the user")
