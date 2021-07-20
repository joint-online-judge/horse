from enum import Enum
from typing import Any
from uuid import UUID


class StrEnumMixin(str, Enum):
    def __str__(self) -> str:
        return self.value


def is_uuid(s: Any) -> bool:
    try:
        UUID(str(s))
    except ValueError:
        return False
    return True
