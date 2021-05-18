import string
from datetime import datetime
from typing import Callable, List, Optional

from pydantic import Field, validator
from pydantic.main import BaseModel
from pydantic.typing import AnyCallable

from joj.horse.schemas.base import (
    BaseODMSchema,
    LongStr,
    LongText,
    ReferenceSchema,
    reference_schema_validator,
)
from joj.horse.schemas.user import UserBase


class DomainEdit(BaseModel):
    name: Optional[LongStr]
    gravatar: Optional[LongStr]
    bulletin: Optional[LongText]
    invitation_code: Optional[LongStr]
    invitation_expire_at: Optional[datetime]


class DomainCreate(BaseModel):
    url: LongStr = Field(..., description="(unique) url of the domain")
    name: LongStr = Field(..., description="displayed name of the domain")
    bulletin: LongText = Field("", description="bulletin of the domain")
    gravatar: LongStr = Field("", description="gravatar url of the domain")

    @validator("url")
    def validate_url(cls, v: str) -> str:
        for c in v:
            if not c in string.ascii_letters + string.digits + "_-":
                raise ValueError("url")
        return v


class Domain(DomainCreate, BaseODMSchema):
    owner: ReferenceSchema[UserBase]

    _validate_owner: Callable[[AnyCallable], classmethod] = reference_schema_validator(
        "owner", UserBase
    )


class ListDomains(BaseModel):
    results: List[Domain]


class ListDomainLabels(BaseModel):
    results: List[str]
