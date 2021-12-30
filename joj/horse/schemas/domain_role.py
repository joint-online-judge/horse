from typing import Any, Dict, Optional

from sqlmodel import Field

from joj.horse.schemas.base import (
    BaseModel,
    BaseORMSchema,
    DomainMixin,
    EditMetaclass,
    IDMixin,
    NoneEmptyLongStr,
    TimestampMixin,
)
from joj.horse.schemas.permission import DomainPermission


class DomainRoleEdit(BaseModel, metaclass=EditMetaclass):
    role: Optional[NoneEmptyLongStr] = Field(None, description="New role name")
    permission: Optional[Dict[str, Any]] = Field(
        None, description="The permission which needs to be updated"
    )


class DomainRoleBase(BaseORMSchema):
    role: NoneEmptyLongStr = Field(nullable=False)
    permission: DomainPermission


class DomainRoleCreate(DomainRoleBase):
    pass


class DomainRole(DomainRoleBase, DomainMixin, IDMixin):
    pass


class DomainRoleDetail(TimestampMixin, DomainRole):
    pass
