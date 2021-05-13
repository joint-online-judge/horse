from enum import IntEnum
from typing import Callable, List, Optional

from pydantic import Field
from pydantic.main import BaseModel
from pydantic.typing import AnyCallable

from joj.horse.schemas.base import (
    BaseODMSchema,
    LongStr,
    LongText,
    NoneEmptyStr,
    ReferenceSchema,
    reference_schema_validator,
)
from joj.horse.schemas.domain import Domain
from joj.horse.schemas.problem_group import ProblemGroup
from joj.horse.schemas.problem_set import ProblemSet
from joj.horse.schemas.user import UserBase


class DataVersion(IntEnum):
    v1 = 1
    v2 = 2


class ProblemEdit(BaseModel):
    title: Optional[NoneEmptyStr]
    content: Optional[LongText]
    data: Optional[int]
    data_version: Optional[DataVersion]
    languages: Optional[List[LongStr]]


class ProblemCreate(BaseModel):
    domain: LongStr = Field(..., description="url or the id of the domain")
    title: NoneEmptyStr = Field(..., description="title of the problem")
    content: LongText = Field("", description="content of the problem")
    data_version: DataVersion = Field(...)
    languages: List[LongStr] = Field(
        [], description="acceptable language of the problem"
    )
    problem_set: LongStr = Field(..., description="problem set it belongs to")


class Problem(ProblemCreate, BaseODMSchema):
    domain: ReferenceSchema[Domain]  # type: ignore
    owner: ReferenceSchema[UserBase]
    problem_group: ReferenceSchema[ProblemGroup]
    problem_set: ReferenceSchema[ProblemSet]  # type: ignore

    num_submit: int = 0
    num_accept: int = 0

    data: Optional[int] = None  # modify later
    total_score: int = 0
    data_version: DataVersion = DataVersion.v2

    _validate_domain: Callable[[AnyCallable], classmethod] = reference_schema_validator(
        "domain", Domain
    )
    _validate_owner: Callable[[AnyCallable], classmethod] = reference_schema_validator(
        "owner", UserBase
    )
    _validate_problem_group: Callable[
        [AnyCallable], classmethod
    ] = reference_schema_validator("problem_group", ProblemGroup)
    _validate_problem_set: Callable[
        [AnyCallable], classmethod
    ] = reference_schema_validator("problem_set", ProblemSet)


class ListProblems(BaseModel):
    results: List[Problem]
