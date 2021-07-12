from datetime import datetime
from typing import Any, Callable, List, Optional

from pydantic import Field, validator
from pydantic.main import BaseModel
from pydantic.typing import AnyCallable

from joj.horse.models.permission import DefaultRole
from joj.horse.schemas.base import (
    BaseODMSchema,
    ReferenceSchema,
    reference_schema_validator,
)
from joj.horse.schemas.domain import Domain
from joj.horse.schemas.user import UserBase


class DomainUser(BaseODMSchema):
    domain: ReferenceSchema[Domain]
    user: ReferenceSchema[UserBase]
    role: str

    join_at: Optional[datetime] = None

    @validator("join_at", pre=True, always=True)
    def default_join_at(cls, v: datetime, *, values: Any, **kwargs: Any) -> datetime:
        return v or datetime.utcnow()

    _validator_domain: Callable[
        [AnyCallable], classmethod
    ] = reference_schema_validator("domain", Domain)
    _validator_user: Callable[[AnyCallable], classmethod] = reference_schema_validator(
        "user", UserBase
    )


class ListDomainUsers(BaseModel):
    results: List[DomainUser]


class DomainUserAdd(BaseModel):
    role: DefaultRole = Field(DefaultRole.USER)
    user: str = Field("me", description="'me' or ObjectId of the user")
