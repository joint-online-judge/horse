from datetime import datetime
from typing import Callable, List, Optional

from pydantic import Field
from pydantic.main import BaseModel
from pydantic.typing import AnyCallable

from joj.horse.schemas.base import (
    BaseODMSchema,
    ReferenceSchema,
    reference_schema_validator,
)
from joj.horse.schemas.user import UserBase


class DomainEdit(BaseModel):
    name: Optional[str]
    gravatar: Optional[str]
    bulletin: Optional[str]
    invitation_code: Optional[str]
    invitation_expire_at: Optional[datetime]


class DomainCreate(BaseModel):
    url: str = Field(..., description="(unique) url of the domain")
    name: str = Field(..., description="displayed name of the domain")
    bulletin: str = Field("", description="bulletin of the domain")
    gravatar: str = Field("", description="gravatar url of the domain")


class Domain(DomainCreate, BaseODMSchema):
    owner: ReferenceSchema[UserBase]

    _validate_owner: Callable[[AnyCallable], classmethod] = reference_schema_validator(
        "owner", UserBase
    )


class ListDomains(BaseModel):
    rows: List[Domain]


class ListDomainLabels(BaseModel):
    rows: List[str]
