from datetime import datetime, timedelta
from typing import List

from joj.horse.schemas import BaseModel
from joj.horse.schemas.user import User


class Score(BaseModel):
    score: int
    time: datetime
    full_score: int
    time_spent: timedelta
    tried: bool


class UserScore(BaseModel):
    user: User
    total_score: int
    total_time_spent: timedelta
    scores: List[Score]


class ScoreBoard(BaseModel):
    problem_ids: List[str]
    results: List[UserScore]
