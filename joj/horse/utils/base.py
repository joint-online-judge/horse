from enum import Enum
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Any, Generator
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


class TemporaryDirectory:
    def __init__(
        self,
        suffix: str | None = None,
        prefix: str | None = None,
        base_dir: str | None = None,
    ) -> None:
        self.suffix = suffix
        self.prefix = prefix
        self.dir = base_dir

    def __call__(self) -> Generator[Path, None, None]:
        path = mkdtemp(suffix=self.suffix, prefix=self.prefix, dir=self.dir)
        try:
            yield Path(path)
        finally:
            rmtree(path, ignore_errors=True)


def iter_file(file_path: Path) -> Generator[bytes, None, None]:
    with file_path.open(mode="rb") as fp:
        yield from fp
