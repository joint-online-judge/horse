from datetime import datetime, timedelta
from typing import Callable, List, Optional

from pydantic import Field
from pydantic.main import BaseModel
from pydantic.typing import AnyCallable

from joj.horse.schemas.base import (
    BaseODMSchema,
    LongText,
    NoneEmptyLongStr,
    ReferenceSchema,
    UserInputURL,
    reference_schema_validator,
)
from joj.horse.schemas.domain import Domain
from joj.horse.schemas.problem import Problem
from joj.horse.schemas.user import UserBase


class ProblemSetEdit(BaseModel):
    title: Optional[NoneEmptyLongStr]
    content: Optional[LongText]
    hidden: Optional[bool]
    scoreboard_hidden: Optional[bool]
    available_time: Optional[datetime]
    due_time: Optional[datetime]


class ProblemSetCreate(BaseModel):
    # domain: LongStr = Field(..., description="url or the id of the domain")
    url: UserInputURL = Field(
        None, description="(unique in domain) url of the problem set"
    )
    title: NoneEmptyLongStr = Field(..., description="title of the problem set")
    content: LongText = Field("", description="content of the problem set")
    hidden: bool = Field(False, description="whether the problem set is hidden")
    scoreboard_hidden: bool = Field(
        False, description="whether the scoreboard of the problem set is hidden"
    )
    available_time: datetime = Field(
        datetime.utcnow(), description="the problem set is available from"
    )
    due_time: datetime = Field(
        datetime.utcnow() + timedelta(days=7), description="the problem set is due at"
    )


class ProblemSet(ProblemSetCreate, BaseODMSchema):
    domain: ReferenceSchema[Domain]
    owner: ReferenceSchema[UserBase]

    url: NoneEmptyLongStr
    num_submit: int = 0
    num_accept: int = 0

    # scoreboard_hidden: bool
    # available_time: datetime
    # due_time: datetime

    problems: List[ReferenceSchema[Problem]] = []

    _validate_domain: Callable[[AnyCallable], classmethod] = reference_schema_validator(
        "domain", Domain
    )
    _validate_owner: Callable[[AnyCallable], classmethod] = reference_schema_validator(
        "owner", UserBase
    )
    _validate_problems: Callable[
        [AnyCallable], classmethod
    ] = reference_schema_validator("problems", Problem, each_item=True)


class ListProblemSets(BaseModel):
    results: List[ProblemSet]
