from typing import Callable, List, Optional

from pydantic import Field
from pydantic.main import BaseModel
from pydantic.typing import AnyCallable

from joj.horse.schemas.base import (
    BaseODMSchema,
    LongStr,
    LongText,
    NoneEmptyLongStr,
    ReferenceSchema,
    reference_schema_validator,
)
from joj.horse.schemas.domain import Domain
from joj.horse.schemas.problem import Problem
from joj.horse.schemas.user import UserBase


class ProblemSetEdit(BaseModel):
    title: Optional[NoneEmptyLongStr]
    content: Optional[LongText]
    hidden: Optional[bool]
    labels: Optional[List[LongStr]]
    problems: Optional[List[LongStr]]


class ProblemSetCreate(BaseModel):
    domain: LongStr = Field(..., description="url or the id of the domain")
    title: NoneEmptyLongStr = Field(..., description="title of the problem set")
    content: LongText = Field("", description="content of the problem set")
    hidden: bool = Field(False, description="whether the problem set is hidden")
    problems: List[LongStr] = Field(
        [], description="problems belonging to the problem set"
    )


class ProblemSet(ProblemSetCreate, BaseODMSchema):
    domain: ReferenceSchema[Domain]  # type: ignore
    owner: ReferenceSchema[UserBase]

    labels: List[LongStr] = []
    num_submit: int = 0
    num_accept: int = 0

    problems: List[ReferenceSchema[Problem]] = []  # type: ignore

    _validate_domain: Callable[[AnyCallable], classmethod] = reference_schema_validator(
        "domain", Domain
    )
    _validate_owner: Callable[[AnyCallable], classmethod] = reference_schema_validator(
        "owner", UserBase
    )
    _validate_problem: Callable[
        [AnyCallable], classmethod
    ] = reference_schema_validator("problems", Problem, each_item=True)


class ListProblemSets(BaseModel):
    results: List[ProblemSet]
