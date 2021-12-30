from datetime import datetime
from typing import Optional

from pydantic import validator
from sqlmodel import Field

from joj.horse.models.permission import DefaultRole
from joj.horse.schemas import BaseModel
from joj.horse.schemas.base import (
    DomainMixin,
    EditMetaclass,
    IDMixin,
    LongStr,
    TimestampMixin,
    URLCreateMixin,
    URLORMSchema,
    UTCDatetime,
    get_datetime_column,
)


class DomainInvitationEdit(BaseModel, metaclass=EditMetaclass):
    code: Optional[LongStr] = Field(None, description="invitation code")
    expire_at: Optional[UTCDatetime] = Field(
        None, description="expire time of invitation"
    )
    role: Optional[str] = Field(None, description="domain role after invitation")


class DomainInvitationBase(URLORMSchema):
    code: LongStr = Field(index=True, nullable=False, description="invitation code")
    expire_at: Optional[datetime] = Field(
        None,
        sa_column=get_datetime_column(nullable=True),
        description="expire time of invitation",
    )
    role: str = Field(
        str(DefaultRole.USER),
        nullable=False,
        sa_column_kwargs={"server_default": str(DefaultRole.USER)},
        description="domain role after invitation",
    )


class DomainInvitationCreate(URLCreateMixin, DomainInvitationBase):
    expire_at: Optional[UTCDatetime]

    @validator("role", pre=True)
    def validate_role(cls, v: str) -> str:
        if v == DefaultRole.ROOT:
            raise ValueError("role can not be root")
        return v


class DomainInvitation(DomainInvitationBase, DomainMixin, IDMixin):
    pass


class DomainInvitationDetail(TimestampMixin, DomainInvitation):
    pass
