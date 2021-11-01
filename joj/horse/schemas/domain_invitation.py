from datetime import datetime
from typing import Optional

from pydantic import Field, validator
from tortoise.contrib.pydantic import pydantic_model_creator

from joj.horse.models.domain_invitation import DomainInvitation as DomainInvitationModel
from joj.horse.models.permission import DefaultRole
from joj.horse.schemas import BaseModel
from joj.horse.schemas.base import LongStr


class DomainInvitationEdit(BaseModel):
    code: Optional[LongStr] = Field(None, description="invitation code")
    expire_at: Optional[datetime] = Field(None, description="expire time of invitation")
    role: Optional[str] = Field(None, description="domain role after invitation")


class DomainInvitationCreate(BaseModel):
    code: LongStr = Field("", description="invitation code")
    expire_at: datetime = Field(datetime.max, description="expire time of invitation")
    role: str = Field(DefaultRole.USER, description="domain role after invitation")

    @validator("role", pre=True)
    def validate_role(cls, v: str) -> str:
        if v == DefaultRole.ROOT:
            raise ValueError("role can not be root")
        return v


DomainInvitation = pydantic_model_creator(
    DomainInvitationModel,
    name="DomainInvitation",
    exclude=("domain",),
)
