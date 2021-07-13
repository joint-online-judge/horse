from typing import List

from pydantic import HttpUrl

from joj.horse.schemas import BaseModel
from joj.horse.schemas.base import BaseODMSchema


class ProblemGroup(BaseODMSchema):
    moss_results: List[HttpUrl] = []


class ListProblemGroups(BaseModel):
    results: List[ProblemGroup]
