from typing import Any, Dict, Optional

from pydantic import Field

# from joj.horse.models.permission import DomainPermission
from joj.horse.schemas import BaseModel
from joj.horse.schemas.base import NoneEmptyLongStr
from joj.horse.schemas.permission import DomainPermission


class DomainRoleEdit(BaseModel):
    role: Optional[NoneEmptyLongStr] = Field(None, description="New role name")
    permission: Optional[Dict[str, Any]] = Field(
        None, description="The permission which needs to be updated"
    )


class DomainRoleCreate(BaseModel):
    role: NoneEmptyLongStr
    permission: DomainPermission = DomainPermission()
