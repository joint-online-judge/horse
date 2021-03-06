from typing import Callable, List, Optional

from pydantic.main import BaseModel
from pydantic.typing import AnyCallable

from joj.horse.schemas.base import (
    BaseODMSchema,
    NoneEmptyStr,
    ReferenceSchema,
    reference_schema_validator,
)
from joj.horse.schemas.domain import Domain
from joj.horse.schemas.problem import Problem
from joj.horse.schemas.user import UserBase


class EditProblemSet(BaseModel):
    title: Optional[NoneEmptyStr]
    content: Optional[str]
    hidden: Optional[bool]


class ProblemSet(BaseODMSchema):
    domain: ReferenceSchema[Domain]
    owner: ReferenceSchema[UserBase]

    title: NoneEmptyStr
    content: str = ""
    hidden: bool = False
    num_submit: int = 0
    num_accept: int = 0

    problems: List[ReferenceSchema[Problem]] = []

    _validate_domain: Callable[[AnyCallable], classmethod] = reference_schema_validator(
        "domain", Domain
    )
    _validate_owner: Callable[[AnyCallable], classmethod] = reference_schema_validator(
        "owner", UserBase
    )
    _validate_problem: Callable[
        [AnyCallable], classmethod
    ] = reference_schema_validator("problems", Problem, each_item=True)
