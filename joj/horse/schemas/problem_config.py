from typing import List
from uuid import UUID

from sqlalchemy.schema import Column
from sqlalchemy.types import JSON
from sqlmodel import Field

from joj.horse.schemas.base import BaseModel, BaseORMSchema, IDMixin, TimestampMixin


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
    languages: List[str] = Field(
        [],
        sa_column=Column(JSON, nullable=False, server_default="[]"),
    )
    commit_id: str = Field("", nullable=False, sa_column_kwargs={"server_default": ""})
    committer_id: UUID | None = None


class ProblemConfigDetail(TimestampMixin, ProblemConfig):
    pass
