from typing import Any, Dict
from uuid import UUID

from sqlalchemy import JSON
from sqlalchemy.schema import Column, ForeignKey, UniqueConstraint
from sqlmodel import Field, Relationship
from sqlmodel.sql.sqltypes import GUID

from joj.horse.models.base import BaseORMModel
from joj.horse.models.domain import Domain
from joj.horse.schemas.domain_role import DomainRoleDetail
from joj.horse.utils.errors import BizError, ErrorCode


class DomainRole(BaseORMModel, DomainRoleDetail, table=True):  # type: ignore[call-arg]
    __tablename__ = "domain_roles"
    __table_args__ = (UniqueConstraint("domain_id", "role"),)

    permission: Dict[str, Any] = Field(
        index=False, sa_column=Column(JSON, nullable=False)
    )

    domain_id: UUID = Field(
        sa_column=Column(
            GUID, ForeignKey("domains.id", ondelete="CASCADE"), nullable=False
        )
    )
    domain: "Domain" = Relationship(back_populates="roles")

    @classmethod
    async def ensure_exists(cls, domain_id: UUID, role: str) -> None:
        if await DomainRole.get_or_none(domain_id=domain_id, role=role) is None:
            raise BizError(ErrorCode.DomainRoleNotFoundError)
