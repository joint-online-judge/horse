from datetime import datetime
from typing import Callable, List, Optional, Type

from pydantic.main import BaseModel
from pydantic.typing import AnyCallable

from joj.horse.schemas.base import (
    BaseODMSchema,
    NoneEmptyStr,
    ReferenceSchema,
    reference_schema_validator,
)
from joj.horse.schemas.domain import Domain
from joj.horse.schemas.problem_group import ProblemGroup
from joj.horse.schemas.user import UserBase


class EditProblem(BaseModel):
    title: Optional[NoneEmptyStr]
    content: Optional[str]
    hidden: Optional[bool]
    data: Optional[int]
    data_version: Optional[int]
    languages: Optional[List[str]]


class Problem(BaseODMSchema):
    domain: ReferenceSchema[Domain]
    owner: ReferenceSchema[UserBase]
    group: ReferenceSchema[ProblemGroup]

    title: NoneEmptyStr
    content: str = ""
    hidden: bool = False
    num_submit: int = 0
    num_accept: int = 0

    data: Optional[int] = None  # modify later
    data_version: int = 2
    languages: List[str] = []

    _validate_domain: Callable[[AnyCallable], classmethod] = reference_schema_validator(
        "domain", Domain
    )
    _validate_owner: Callable[[AnyCallable], classmethod] = reference_schema_validator(
        "owner", UserBase
    )
    _validate_group: Callable[[AnyCallable], classmethod] = reference_schema_validator(
        "group", ProblemGroup
    )
