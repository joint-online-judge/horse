from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.schema import Column, ForeignKey, UniqueConstraint
from sqlalchemy.types import JSON
from sqlmodel import Field, Relationship
from sqlmodel.sql.sqltypes import GUID

from joj.horse.models.base import BaseORMModel
from joj.horse.models.domain import Domain
from joj.horse.schemas.base import BaseModel, NoneEmptyLongStr
from joj.horse.schemas.permission import DomainPermission
from joj.horse.utils.errors import BizError, ErrorCode


class DomainRoleEdit(BaseModel):
    role: Optional[NoneEmptyLongStr] = Field(None, description="New role name")
    permission: Optional[Dict[str, Any]] = Field(
        None, description="The permission which needs to be updated"
    )


class DomainRoleCreate(BaseModel):
    role: NoneEmptyLongStr
    permission: DomainPermission = DomainPermission()


class DomainRole(BaseORMModel, table=True):  # type: ignore[call-arg]
    __tablename__ = "domain_roles"
    __table_args__ = (UniqueConstraint("domain_id", "role"),)

    role: str = Field(index=False)
    permission: Dict[str, Any] = Field(index=False, sa_column=Column(JSON))

    domain_id: UUID = Field(
        sa_column=Column(GUID, ForeignKey("domains.id", ondelete="CASCADE"))
    )
    domain: Optional["Domain"] = Relationship(back_populates="roles")

    @classmethod
    async def ensure_exists(cls, domain_id: UUID, role: str) -> None:
        if await DomainRole.get_or_none(domain_id=domain_id, role=role) is None:
            raise BizError(ErrorCode.DomainRoleNotFoundError)
