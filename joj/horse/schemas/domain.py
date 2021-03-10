from typing import Callable, Optional

from pydantic.main import BaseModel
from pydantic.typing import AnyCallable

from joj.horse.schemas.base import (
    BaseODMSchema,
    ReferenceSchema,
    reference_schema_validator,
)
from joj.horse.schemas.user import UserBase


class EditDomain(BaseModel):
    name: Optional[str]
    gravatar: Optional[str]
    bulletin: Optional[str]


class Domain(BaseODMSchema):
    url: str
    name: str
    owner: ReferenceSchema[UserBase]

    gravatar: str = ""
    bulletin: str = ""

    _validate_owner: Callable[[AnyCallable], classmethod] = reference_schema_validator(
        "owner", UserBase
    )
