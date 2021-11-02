from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import validator
from sqlalchemy import event
from sqlalchemy.schema import Column, ForeignKey, UniqueConstraint
from sqlmodel import Field, Relationship
from sqlmodel.sql.sqltypes import GUID

from joj.horse.models.base import (
    DomainURLORMModel,
    URLMixin,
    UTCDatetime,
    get_datetime_column,
    url_pre_save,
)
from joj.horse.models.domain import Domain
from joj.horse.models.permission import DefaultRole
from joj.horse.schemas import BaseModel
from joj.horse.schemas.base import LongStr


class DomainInvitationBase(URLMixin):
    code: LongStr = Field("", nullable=False, description="invitation code")
    expire_at: datetime = Field(
        datetime.max,
        sa_column=get_datetime_column(index=False),
        description="expire time of invitation",
    )
    role: str = Field(
        DefaultRole.USER,
        index=False,
        nullable=False,
        description="domain role after invitation",
    )


class DomainInvitationEdit(BaseModel):
    code: Optional[LongStr] = Field(None, description="invitation code")
    expire_at: Optional[UTCDatetime] = Field(
        None, description="expire time of invitation"
    )
    role: Optional[str] = Field(None, description="domain role after invitation")


class DomainInvitationCreate(DomainInvitationBase):
    expire_at: UTCDatetime

    @validator("role", pre=True)
    def validate_role(cls, v: str) -> str:
        if v == DefaultRole.ROOT:
            raise ValueError("role can not be root")
        return v


class DomainInvitation(DomainURLORMModel, DomainInvitationBase, table=True):  # type: ignore[call-arg]
    __tablename__ = "domain_invitations"
    __table_args__ = (UniqueConstraint("domain_id", "code"),)

    domain_id: UUID = Field(
        sa_column=Column(GUID, ForeignKey("domains.id", ondelete="CASCADE"))
    )
    domain: Optional["Domain"] = Relationship(back_populates="invitations")


event.listen(DomainInvitation, "before_insert", url_pre_save)
event.listen(DomainInvitation, "before_update", url_pre_save)
