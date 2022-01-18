from datetime import datetime
from enum import Enum, IntEnum
from typing import List, Optional
from uuid import UUID

from sqlalchemy import JSON
from sqlalchemy.schema import Column
from sqlmodel import Field

from joj.horse.schemas import BaseModel
from joj.horse.schemas.base import BaseORMSchema, DomainMixin, IDMixin, TimestampMixin
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


class RecordCaseResult(IntEnum):
    accepted = 1
    wrong_answer = 2
    time_limit_exceeded = 3
    memory_limit_exceeded = 4
    output_limit_exceeded = 5
    runtime_error = 6
    compile_error = 7
    system_error = 8
    canceled = 9
    etc = 10


class RecordCodeType(StrEnumMixin, Enum):
    text = "text"
    archive = "archive"


class RecordCase(BaseModel):
    state: RecordCaseResult = RecordCaseResult.etc
    score: int = 0
    time_ms: int = 0
    memory_kb: int = 0
    return_code: int = 0


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


# class Record(BaseODMSchema):
#     status: RecordStatus = RecordStatus.waiting
#     score: int = 0
#     time_ms: int = 0
#     memory_kb: int = 0
#     domain: ReferenceSchema[Domain]
#     problem: ReferenceSchema[Problem]
#     problem_data: int = 0
#     user: ReferenceSchema[UserBase]
#     code_type: RecordCodeType
#     code: str
#     judge_category: List[str]
#
#     submit_at: datetime
#     judge_at: Optional[datetime]
#
#     judge_user: Optional[ReferenceSchema[UserBase]]
#
#     compiler_texts: str = ""
#     cases: List[RecordCase] = []
#
#     _validate_domain: Callable[[AnyCallable], classmethod] = reference_schema_validator(
#         "domain", Domain
#     )
#     _validate_user: Callable[[AnyCallable], classmethod] = reference_schema_validator(
#         "user", UserBase
#     )
#     _validate_judge_user: Callable[
#         [AnyCallable], classmethod
#     ] = reference_schema_validator("judge_user", UserBase)
#     _validate_problem: Callable[
#         [AnyCallable], classmethod
#     ] = reference_schema_validator("problem", Problem)


class ListRecords(BaseModel):
    results: List[Record]


# class RecordCaseResult(BaseModel):
#     index: int
#     result: RecordCase


class RecordResult(BaseModel):
    state: RecordState
    score: int
    time_ms: int
    memory_kb: int
    judge_at: datetime
