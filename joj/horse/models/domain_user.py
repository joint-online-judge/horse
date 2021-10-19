from typing import Optional, Union
from uuid import UUID

from sqlalchemy.schema import Column, ForeignKey, UniqueConstraint
from sqlmodel import Field, Relationship
from sqlmodel.sql.sqltypes import GUID

from joj.horse.models.base import BaseORMModel
from joj.horse.models.domain import Domain
from joj.horse.models.domain_role import DomainRole
from joj.horse.models.permission import DefaultRole
from joj.horse.models.user import User
from joj.horse.schemas.base import BaseModel
from joj.horse.schemas.permission import DomainPermission
from joj.horse.utils.errors import BizError, ErrorCode


class DomainUserAdd(BaseModel):
    role: DefaultRole = Field(DefaultRole.USER)
    user: str = Field(..., description="'me' or ObjectId of the user")


class DomainUserPermission(BaseModel):
    permission: DomainPermission


class DomainUser(BaseORMModel, table=True):  # type: ignore[call-arg]
    __tablename__ = "domain_users"
    __table_args__ = (UniqueConstraint("domain_id", "user_id"),)

    role: str = Field(index=False)

    domain_id: UUID = Field(
        sa_column=Column(GUID, ForeignKey("domains.id", ondelete="CASCADE"))
    )
    domain: Optional["Domain"] = Relationship(back_populates="users")

    user_id: UUID = Field(
        sa_column=Column(GUID, ForeignKey("users.id", ondelete="CASCADE"))
    )
    user: Optional["User"] = Relationship(back_populates="domain_users")

    @classmethod
    async def add_domain_user(
        cls, domain: Domain, user: User, role: Union[str, DefaultRole]
    ) -> "DomainUser":
        role = str(role)
        # check domain user
        if await DomainUser.get_or_none(domain=domain, user=user):
            raise BizError(ErrorCode.UserAlreadyInDomainBadRequestError)
        # check domain role
        await DomainRole.ensure_exists(domain=domain, role=role)
        # add member
        domain_user = await DomainUser.create(domain=domain, user=user, role=role)
        return domain_user

    @classmethod
    async def update_domain_user(
        cls, domain: Domain, user: User, role: Union[str, DefaultRole]
    ) -> "DomainUser":
        role = str(role)
        # check domain user
        domain_user = await DomainUser.get_or_none(domain=domain, user=user)
        if domain_user is None:
            raise BizError(ErrorCode.UserAlreadyInDomainBadRequestError)
        # check domain role
        await DomainRole.ensure_exists(domain=domain, role=role)
        # update role
        domain_user.role = role
        await domain_user.save()
        return domain_user
