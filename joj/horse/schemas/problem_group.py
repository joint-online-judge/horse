from typing import List

from pydantic import HttpUrl

from joj.horse.schemas import BaseModel


class ProblemGroup(BaseModel):
    moss_results: List[HttpUrl] = []


class ListProblemGroups(BaseModel):
    results: List[ProblemGroup]
