from datetime import datetime
from typing import Any, Callable, Dict

from pydantic import validator
from pydantic.typing import AnyCallable

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
    permission: Dict[str, Any] = {}

    updated_at: datetime = datetime.utcnow()

    @validator("permission", pre=True, always=True)
    def default_permission(cls, v, *, values, **kwargs):
        return v or DomainPermission().dump()

    @validator("updated_at", pre=True, always=True)
    def default_updated_at(cls, v, *, values, **kwargs):
        return v or datetime.utcnow()

    _validator_domain: Callable[
        [AnyCallable], classmethod
    ] = reference_schema_validator("domain", Domain)
