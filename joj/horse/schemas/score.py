from datetime import datetime, timedelta
from typing import List

from joj.horse.models.user import UserBase
from joj.horse.schemas import BaseModel
from joj.horse.schemas.base import PydanticObjectId


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
