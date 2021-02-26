from typing import Callable

from pydantic.typing import AnyCallable

from joj.horse.schemas.base import (
    BaseODMSchema,
    ReferenceSchema,
    reference_schema_validator,
)
from joj.horse.schemas.user import UserBase


class Domain(BaseODMSchema):
    url: str
    name: str
    owner: ReferenceSchema[UserBase]

    gravatar: str = ""
    bulletin: str = ""

    _validate_owner: Callable[[AnyCallable], classmethod] = reference_schema_validator(
        "owner", UserBase
    )
