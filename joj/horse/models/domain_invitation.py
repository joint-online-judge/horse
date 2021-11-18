from uuid import UUID

from sqlalchemy import event
from sqlalchemy.schema import Column, ForeignKey, UniqueConstraint
from sqlmodel import Field, Relationship
from sqlmodel.sql.sqltypes import GUID

from joj.horse.models.base import DomainURLORMModel, url_pre_save
from joj.horse.models.domain import Domain
from joj.horse.schemas.domain_invitation import DomainInvitationDetail


class DomainInvitation(DomainURLORMModel, DomainInvitationDetail, table=True):  # type: ignore[call-arg]
    __tablename__ = "domain_invitations"
    __table_args__ = (
        UniqueConstraint("domain_id", "url"),
        UniqueConstraint("domain_id", "code"),
    )

    domain_id: UUID = Field(
        sa_column=Column(
            GUID, ForeignKey("domains.id", ondelete="CASCADE"), nullable=False
        )
    )
    domain: "Domain" = Relationship(back_populates="invitations")


event.listen(DomainInvitation, "before_insert", url_pre_save)
event.listen(DomainInvitation, "before_update", url_pre_save)
