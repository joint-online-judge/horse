import uuid
from enum import Enum
from typing import Any


class StrEnumMixin(str, Enum):
    def __str__(self) -> str:
        return self.value


def is_uuid(s: Any) -> bool:
    try:
        uuid.UUID(str(s))
    except ValueError:
        return False
    return True
