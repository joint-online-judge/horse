from enum import Enum
from typing import Optional
from uuid import UUID

from sqlmodel import Field

from joj.elephant.schemas import Config, StrEnumMixin
from joj.horse.schemas.base import BaseModel, BaseORMSchema, IDMixin, TimestampMixin


class ConfigJsonOnMissing(StrEnumMixin, Enum):
    use_old = "use_old"
    use_default = "use_default"
    raise_error = "raise_error"


class ProblemConfigBase(BaseORMSchema):
    commit_message: str = Field(
        "", nullable=False, sa_column_kwargs={"server_default": ""}
    )
    data_version: int = Field(
        2, nullable=False, sa_column_kwargs={"server_default": "2"}
    )


class ProblemConfigCommit(BaseModel):
    message: str = ""
    data_version: int = 2


class ProblemConfig(ProblemConfigBase, IDMixin):
    commit_id: str = Field("", nullable=False, sa_column_kwargs={"server_default": ""})
    committer_id: Optional[UUID] = None


class ProblemConfigDetail(TimestampMixin, ProblemConfig):
    pass


class ProblemConfigJson(Config):
    pass


class ProblemConfigDataDetail(ProblemConfigDetail):
    data: ProblemConfigJson
