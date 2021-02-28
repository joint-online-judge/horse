from typing import Callable, List, Optional

from pydantic import ConstrainedStr
from pydantic.main import BaseModel
from pydantic.types import constr
from pydantic.typing import AnyCallable

from joj.horse.schemas.base import (
    BaseODMSchema,
    ReferenceSchema,
    reference_schema_validator,
)
from joj.horse.schemas.domain import Domain
from joj.horse.schemas.problem import Problem
from joj.horse.schemas.user import UserBase


# TODO: validate the title is non-empty
class EditProblemSet(BaseModel):
    title: Optional[str]
    content: Optional[str]
    hidden: Optional[bool]


class ProblemSet(BaseODMSchema):
    domain: ReferenceSchema[Domain]
    owner: ReferenceSchema[UserBase]

    title: str
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
