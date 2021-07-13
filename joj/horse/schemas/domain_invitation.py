from datetime import datetime
from typing import Callable, Optional

from pydantic import Field, validator
from pydantic.typing import AnyCallable

from joj.horse.models.permission import DefaultRole
from joj.horse.schemas import BaseModel
from joj.horse.schemas.base import (
    BaseODMSchema,
    LongStr,
    ReferenceSchema,
    reference_schema_validator,
)
from joj.horse.schemas.domain import Domain


class DomainInvitationEdit(BaseModel):
    code: Optional[LongStr] = Field(None, description="invitation code")
    expire_at: Optional[datetime] = Field(None, description="expire time of invitation")
    role: Optional[str] = Field(None, description="domain role after invitation")


class DomainInvitationCreate(BaseModel):
    code: LongStr = Field("", description="invitation code")
    expire_at: datetime = Field(datetime.max, description="expire time of invitation")
    role: str = Field(DefaultRole.USER, description="domain role after invitation")


class DomainInvitation(DomainInvitationCreate, BaseODMSchema):
    domain: ReferenceSchema[Domain]

    @validator("role", pre=True)
    def validate_uname(cls, v: str) -> str:
        if v == DefaultRole.ROOT:
            raise ValueError("role can not be root")
        return v

    _validator_domain: Callable[
        [AnyCallable], classmethod
    ] = reference_schema_validator("domain", Domain)
