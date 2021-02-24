from datetime import datetime
from typing import Any, Dict

from pydantic import validator

from joj.horse.models.permission import DomainPermission
from joj.horse.schemas.base import (
    BaseODMSchema,
    ReferenceSchema,
    reference_schema_validator,
)
from joj.horse.schemas.domain import Domain


class DomainRole(BaseODMSchema):
    domain: ReferenceSchema[Domain]
    role: str
    permission: Dict[str, Any] = None

    updated_at: datetime = None

    @validator("permission", pre=True, always=True)
    def default_permission(cls, v, *, values, **kwargs):
        return v or DomainPermission().dump()

    @validator("updated_at", pre=True, always=True)
    def default_updated_at(cls, v, *, values, **kwargs):
        return v or datetime.utcnow()

    _validator_domain = reference_schema_validator("domain", Domain)
