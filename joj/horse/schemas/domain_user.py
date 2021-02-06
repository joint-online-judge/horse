from datetime import datetime

from pydantic import validator

from joj.horse.schemas.base import BaseODMSchema, EmbeddedSchema, embedded_schema
from joj.horse.schemas.domain import Domain
from joj.horse.schemas.user import UserBase


class DomainUser(BaseODMSchema):
    domain: EmbeddedSchema[Domain]
    user: EmbeddedSchema[UserBase]
    role: str

    join_at: datetime = None

    @validator("join_at", pre=True, always=True)
    def default_join_at(cls, v, *, values, **kwargs):
        return v or datetime.utcnow()

    _validator_domain = embedded_schema('domain', Domain)
    _validator_user = embedded_schema('user', UserBase)
