from enum import IntEnum
from typing import Optional

from pymongo import ASCENDING, DESCENDING

from joj.horse.schemas import BaseModel


class SortEnum(IntEnum):
    asc = ASCENDING
    des = DESCENDING


class BaseQuery(BaseModel):
    sort: Optional[SortEnum]
    skip: Optional[int]
    limit: Optional[int]
