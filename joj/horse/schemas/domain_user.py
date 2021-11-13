from typing import TYPE_CHECKING
from uuid import UUID

from sqlmodel import Field

from joj.horse.models.permission import DefaultRole
from joj.horse.schemas.base import BaseModel
from joj.horse.schemas.permission import DomainPermission

if TYPE_CHECKING:
    pass


class DomainUserAdd(BaseModel):
    role: DefaultRole = Field(DefaultRole.USER)
    user: str = Field(..., description="'me' or id of the user")


class DomainUserUpdate(BaseModel):
    role: DefaultRole = Field(DefaultRole.USER)


class DomainUserPermission(BaseModel):
    domain_id: UUID
    user_id: UUID
    role: str
    permission: DomainPermission
