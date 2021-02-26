from datetime import datetime
from typing import Callable

from pydantic import validator
from pydantic.typing import AnyCallable

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

    join_at: datetime = datetime.utcnow()

    @validator("join_at", pre=True, always=True)
    def default_join_at(cls, v, *, values, **kwargs):
        return v or datetime.utcnow()

    _validator_domain: Callable[
        [AnyCallable], classmethod
    ] = reference_schema_validator("domain", Domain)
    _validator_user: Callable[[AnyCallable], classmethod] = reference_schema_validator(
        "user", UserBase
    )
