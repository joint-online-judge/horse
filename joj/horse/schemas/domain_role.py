from typing import Any, Dict

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
    # role: NoneEmptyLongStr | None = Field(None, description="New role name")
    permission: Dict[str, Any] | None = Field(
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
