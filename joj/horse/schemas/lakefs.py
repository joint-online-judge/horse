from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel as PydanticBaseModel

from joj.horse.schemas import BaseModel
from joj.horse.schemas.base import NoneNegativeInt
from joj.horse.utils.base import StrEnumMixin


class FileStats(PydanticBaseModel):
    path: str
    checksum: str
    mtime: str
    size_bytes: int = 0


LAKEFS_RESET_TYPE_MAPPING = {
    "file": "object",
    "dir": "common_prefix",
    "all": "reset",
}


class LakeFSReset(PydanticBaseModel):
    type: Literal["file", "dir", "all"] = "all"
    path: str = ""

    def get_lakefs_type(self) -> str:
        return LAKEFS_RESET_TYPE_MAPPING.get(self.type, "")


class Pagination(PydanticBaseModel):
    has_more: bool
    next_offset: str
    results: NoneNegativeInt
    max_per_page: NoneNegativeInt


class DiffTypeEnum(StrEnumMixin, Enum):
    added = "added"
    removed = "removed"
    changed = "changed"
    conflict = "conflict"


class PathTypeEnum(StrEnumMixin, Enum):
    common_prefix = "common_prefix"
    object = "object"


class Diff(PydanticBaseModel):
    type: DiffTypeEnum
    path: str
    path_type: PathTypeEnum
    size_bytes: Optional[int]


class DiffList(BaseModel):
    pagination: Pagination
    results: List[Diff]


class ObjectStats(PydanticBaseModel):
    path: str
    path_type: PathTypeEnum
    # physical_address: str
    checksum: str
    size_bytes: Optional[int]
    mtime: int
    # metaData: Any
    content_type: Optional[str]


class ObjectStatsList(BaseModel):
    pagination: Pagination
    results: List[ObjectStats]
