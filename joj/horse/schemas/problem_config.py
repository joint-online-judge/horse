from sqlmodel import Field

from joj.horse.schemas.base import BaseModel, BaseORMSchema, IDMixin, TimestampMixin


class ProblemConfigCommit(BaseModel):
    message: str = ""
    data_version: int = 2


class ProblemConfig(BaseORMSchema, IDMixin):
    commit_id: str
    data_version: int = Field(
        2, index=False, nullable=False, sa_column_kwargs={"server_default": "2"}
    )
    languages: str = Field(
        "[]", index=False, nullable=False, sa_column_kwargs={"server_default": "[]"}
    )


class ProblemConfigDetail(TimestampMixin, ProblemConfig):
    pass
