from datetime import datetime, timedelta
from typing import List

from pydantic.main import BaseModel

from joj.horse.schemas.base import PydanticObjectId
from joj.horse.schemas.user import UserBase


class Score(BaseModel):
    score: int
    time: datetime
    full_score: int
    time_spent: timedelta
    tried: bool


class UserScore(BaseModel):
    user: UserBase
    total_score: int
    total_time_spent: timedelta
    scores: List[Score]


class ScoreBoard(BaseModel):
    problem_ids: List[PydanticObjectId]
    results: List[UserScore]
