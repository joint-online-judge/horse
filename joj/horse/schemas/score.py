from datetime import datetime, timedelta
from typing import List

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


class Score(BaseModel):
    score: int
    time: datetime
    full_score: int
    time_spent: timedelta


class UserScore(BaseModel):
    rank: int
    user: UserBase
    total_score: int
    total_time_spent: timedelta
    scores: List[Score]


class ListUserScores(BaseModel):
    results: List[UserScore]
