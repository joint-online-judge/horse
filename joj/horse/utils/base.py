from enum import Enum


class StrEnumMixin(str, Enum):
    def __str__(self) -> str:
        return self.value
