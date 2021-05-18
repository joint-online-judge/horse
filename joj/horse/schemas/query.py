from enum import IntEnum
from typing import Optional

from pydantic import BaseModel
from pymongo import ASCENDING, DESCENDING


class SortEnum(IntEnum):
    asc = ASCENDING
    des = DESCENDING


class BaseQuery(BaseModel):
    sort: Optional[SortEnum]
    skip: Optional[int]
    limit: Optional[int]
