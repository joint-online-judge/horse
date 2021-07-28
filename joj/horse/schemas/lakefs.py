from typing import Literal

from pydantic import BaseModel


class FileStats(BaseModel):
    path: str
    checksum: str
    mtime: str
    size_bytes: int = 0


LAKEFS_RESET_TYPE_MAPPING = {
    "file": "object",
    "dir": "common_prefix",
    "all": "reset",
}


class LakeFSReset(BaseModel):
    type: Literal["file", "dir", "all"] = "all"
    path: str = ""

    def get_lakefs_type(self) -> str:
        return LAKEFS_RESET_TYPE_MAPPING.get(self.type, "")
