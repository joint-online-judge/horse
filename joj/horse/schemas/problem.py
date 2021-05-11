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
from joj.horse.schemas.user import UserBase


class ProblemEdit(BaseModel):
    title: Optional[NoneEmptyStr]
    content: Optional[LongText]
    hidden: Optional[bool]
    data: Optional[int]
    data_version: Optional[int]
    languages: Optional[List[LongStr]]


class ProblemCreate(BaseModel):
    domain: LongStr = Field(..., description="url or the id of the domain")
    title: NoneEmptyStr = Field(..., description="title of the problem")
    content: LongText = Field("", description="content of the problem")
    hidden: bool = Field(False, description="whether the problem is hidden")
    languages: List[LongStr] = Field(
        [], description="acceptable language of the problem"
    )


class Problem(ProblemCreate, BaseODMSchema):
    domain: ReferenceSchema[Domain]  # type: ignore
    owner: ReferenceSchema[UserBase]
    group: ReferenceSchema[ProblemGroup]

    num_submit: int = 0
    num_accept: int = 0

    data: Optional[int] = None  # modify later
    total_score: int = 0
    data_version: int = 2

    _validate_domain: Callable[[AnyCallable], classmethod] = reference_schema_validator(
        "domain", Domain
    )
    _validate_owner: Callable[[AnyCallable], classmethod] = reference_schema_validator(
        "owner", UserBase
    )
    _validate_group: Callable[[AnyCallable], classmethod] = reference_schema_validator(
        "group", ProblemGroup
    )


class ListProblems(BaseModel):
    results: List[Problem]
