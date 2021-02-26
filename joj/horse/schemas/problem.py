from typing import Optional, List
from datetime import datetime

from pydantic import validator

from joj.horse.schemas.base import (
    BaseODMSchema,
    ReferenceSchema,
    reference_schema_validator,
)
from joj.horse.schemas.user import UserBase
from joj.horse.schemas.domain import Domain


class Problem(BaseODMSchema):
    domain: ReferenceSchema[Domain]
    owner: ReferenceSchema[UserBase]

    title: str
    content: str = ""
    hidden: bool = False
    num_submit: int = 0
    num_accept: int = 0

    data: Optional[int] = None  # modify later
    data_version: int = 2
    languages: List[str] = []

    _validate_domain = reference_schema_validator("domain", Domain)
    _validate_owner = reference_schema_validator("owner", UserBase)
