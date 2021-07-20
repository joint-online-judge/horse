from typing import List

from joj.horse.schemas import BaseModel
from joj.horse.schemas.base import NoneNegativeInt, PaginationLimit


class OrderingQuery(BaseModel):
    orderings: List[str]


class PaginationQuery(BaseModel):
    offset: NoneNegativeInt
    limit: PaginationLimit
