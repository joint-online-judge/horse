from typing import Callable, List, Optional

from pydantic import Field
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


class ProblemSetEdit(BaseModel):
    title: Optional[NoneEmptyStr]
    content: Optional[str]
    hidden: Optional[bool]
    labels: Optional[List[str]]
    problems: Optional[List[ReferenceSchema[Problem]]]


class ProblemSetCreate(BaseModel):
    domain: str = Field(..., description="url or the id of the domain")
    title: str = Field(..., description="title of the problem set")
    content: str = Field("", description="content of the problem set")
    hidden: bool = Field(False, description="whether the problem set is hidden")
    problems: List[str] = Field([], description="problems belonging to the problem set")


class ProblemSet(ProblemSetCreate, BaseODMSchema):
    domain: ReferenceSchema[Domain]  # type: ignore
    owner: ReferenceSchema[UserBase]

    labels: List[str] = []
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
