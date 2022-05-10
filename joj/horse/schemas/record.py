from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

from sqlalchemy import JSON
from sqlalchemy.schema import Column
from sqlmodel import Field

from joj.horse.schemas import BaseModel
from joj.horse.schemas.base import (
    BaseORMSchema,
    DomainMixin,
    EditMetaclass,
    IDMixin,
    TimestampMixin,
)
from joj.horse.utils.base import StrEnumMixin


class RecordState(StrEnumMixin, Enum):
    # waiting
    processing = "processing"  # upload the submission to S3
    queueing = "queueing"  # queue in celery
    retrying = "retrying"  # retry in celery
    # working
    fetched = "fetched"  # fetched by a celery worker
    compiling = "compiling"  # only for compiling languages
    running = "running"
    judging = "judging"
    # fetched = 22
    # ignored = 30
    # done
    accepted = "accepted"
    rejected = "rejected"
    failed = "failed"


class RecordCaseResult(StrEnumMixin, Enum):
    accepted = "accepted"
    wrong_answer = "wrong_answer"
    time_limit_exceeded = "time_limit_exceeded"
    memory_limit_exceeded = "memory_limit_exceeded"
    output_limit_exceeded = "output_limit_exceeded"
    runtime_error = "runtime_error"
    compile_error = "compile_error"
    system_error = "system_error"
    canceled = "canceled"
    etc = "etc"


class RecordCase(BaseModel):
    state: RecordCaseResult = RecordCaseResult.etc
    score: int = 0
    time_ms: int = 0
    memory_kb: int = 0
    return_code: int = 0
    stdout: str = ""
    stderr: str = ""


class Record(BaseORMSchema, DomainMixin, IDMixin, TimestampMixin):
    state: RecordState = Field(
        RecordState.processing,
        nullable=False,
        sa_column_kwargs={"server_default": str(RecordState.processing)},
    )
    language: str = Field(nullable=False, sa_column_kwargs={"server_default": ""})

    score: int = Field(0, nullable=False, sa_column_kwargs={"server_default": "0"})
    time_ms: int = Field(0, nullable=False, sa_column_kwargs={"server_default": "0"})
    memory_kb: int = Field(0, nullable=False, sa_column_kwargs={"server_default": "0"})
    judged_at: Optional[datetime]


class RecordListDetail(Record):
    problem_set_id: Optional[UUID] = None
    problem_set_title: Optional[str] = None
    problem_id: Optional[UUID] = None
    problem_title: Optional[str] = None

    @classmethod
    def from_row(
        cls,
        record: "Record",
        problem_title: Optional[str],
        problem_set_title: Optional[str],
    ) -> "RecordListDetail":
        return cls(
            **record.dict(),
            problem_title=problem_title,
            problem_set_title=problem_set_title,
        )


class RecordDetail(Record):
    commit_id: Optional[str] = Field(None, nullable=True)
    task_id: Optional[UUID] = Field(None, nullable=True)

    cases: List[RecordCase] = Field(
        [],
        sa_column=Column(JSON, nullable=False, server_default="[]"),
    )

    problem_set_id: Optional[UUID] = None
    problem_id: Optional[UUID] = None
    problem_config_id: Optional[UUID] = None
    committer_id: Optional[UUID] = None
    judger_id: Optional[UUID] = None


class RecordPreview(IDMixin):
    state: RecordState
    created_at: datetime


class RecordSubmit(BaseModel, metaclass=EditMetaclass):
    state: Optional[RecordState]
    score: Optional[int]
    time_ms: Optional[int]
    memory_kb: Optional[int]
    judged_at: Optional[datetime]


class RecordCaseSubmit(BaseModel, metaclass=EditMetaclass):
    state: Optional[RecordCaseResult]
    score: Optional[int]
    time_ms: Optional[int]
    memory_kb: Optional[int]
    return_code: Optional[int]
    stdout: Optional[str]
    stderr: Optional[str]
