from typing import List

from pydantic import HttpUrl

from joj.horse.schemas.base import BaseODMSchema


class ProblemGroup(BaseODMSchema):
    moss_results: List[HttpUrl] = []
