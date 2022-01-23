from typing import TYPE_CHECKING, Union
from uuid import UUID

from sqlalchemy.schema import Column, ForeignKey, UniqueConstraint
from sqlalchemy.sql.functions import count
from sqlmodel import Field, Relationship, select
from sqlmodel.sql.sqltypes import GUID

from joj.horse.models.base import BaseORMModel
from joj.horse.models.domain import Domain
from joj.horse.models.domain_role import DomainRole
from joj.horse.models.permission import DefaultRole
from joj.horse.utils.errors import BizError, ErrorCode

if TYPE_CHECKING:
    from joj.horse.models.user import User


class DomainUser(BaseORMModel, table=True):  # type: ignore[call-arg]
    __tablename__ = "domain_users"
    __table_args__ = (UniqueConstraint("domain_id", "user_id"),)

    role: str

    domain_id: UUID = Field(
        sa_column=Column(
            GUID, ForeignKey("domains.id", ondelete="CASCADE"), nullable=False
        )
    )
    domain: "Domain" = Relationship(back_populates="users")

    user_id: UUID = Field(
        sa_column=Column(
            GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        )
    )
    user: "User" = Relationship(back_populates="domain_users")

    @classmethod
    async def add_domain_user(
        cls, domain_id: UUID, user_id: UUID, role: Union[str, DefaultRole]
    ) -> "DomainUser":
        role = str(role)
        # check domain user
        domain_user = await DomainUser.get_or_none(domain_id=domain_id, user_id=user_id)
        if domain_user is not None:
            raise BizError(ErrorCode.UserAlreadyInDomainBadRequestError)
        # check domain role
        await DomainRole.ensure_exists(domain_id=domain_id, role=role)
        # add member
        domain_user = DomainUser(domain_id=domain_id, user_id=user_id, role=role)
        return domain_user

    @classmethod
    async def update_domain_user(
        cls, domain_id: UUID, user_id: UUID, role: Union[str, DefaultRole]
    ) -> "DomainUser":
        role = str(role)
        # check domain user
        domain_user = await DomainUser.get_or_none(domain_id=domain_id, user_id=user_id)
        if domain_user is None:
            raise BizError(ErrorCode.UserAlreadyInDomainBadRequestError)
        # check domain role
        await DomainRole.ensure_exists(domain_id=domain_id, role=role)
        # update role
        domain_user.role = role
        return domain_user

    @classmethod
    async def count_domain_user(
        cls, domain_id: UUID, role: Union[str, DefaultRole]
    ) -> int:
        role = str(role)
        statement = (
            select(DomainUser.id)
            .where(DomainUser.domain_id == domain_id)
            .where(DomainUser.role == role)
            .with_only_columns(count())
        )
        user_count = (await DomainUser.session_exec(statement)).one_or_none()
        return 0 if user_count is None else user_count
