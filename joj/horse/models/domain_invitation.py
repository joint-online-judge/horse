from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import validator
from sqlalchemy.schema import Column, ForeignKey, UniqueConstraint
from sqlmodel import Field, Relationship
from sqlmodel.sql.sqltypes import GUID

from joj.horse.models.base import BaseORMModel
from joj.horse.models.domain import Domain
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


class DomainInvitation(BaseORMModel, table=True):  # type: ignore[call-arg]
    __tablename__ = "domain_invitations"
    __table_args__ = (UniqueConstraint("domain_id", "code"),)

    code: str = Field()
    role: str = Field(index=False)
    expire_at: datetime = Field(index=False)

    domain_id: UUID = Field(
        sa_column=Column(GUID, ForeignKey("domains.id", ondelete="CASCADE"))
    )
    domain: Optional["Domain"] = Relationship(back_populates="invitations")
