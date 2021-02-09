from datetime import datetime

from pydantic import validator

from joj.horse.schemas.base import BaseODMSchema, ReferenceSchema, reference_schema_validator
from joj.horse.schemas.domain import Domain
from joj.horse.schemas.user import UserBase


class DomainUser(BaseODMSchema):
    domain: ReferenceSchema[Domain]
    user: ReferenceSchema[UserBase]
    role: str

    join_at: datetime = None

    @validator("join_at", pre=True, always=True)
    def default_join_at(cls, v, *, values, **kwargs):
        return v or datetime.utcnow()

    _validator_domain = reference_schema_validator('domain', Domain)
    _validator_user = reference_schema_validator('user', UserBase)
