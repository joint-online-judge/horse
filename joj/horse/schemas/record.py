from datetime import datetime
from enum import IntEnum
from typing import Callable, List, Optional

from pydantic import validator
from pydantic.main import BaseModel
from pydantic.typing import AnyCallable

from joj.horse.schemas.base import (
    BaseODMSchema,
    PydanticObjectId,
    ReferenceSchema,
    reference_schema_validator,
)
from joj.horse.schemas.domain import Domain
from joj.horse.schemas.problem import Problem
from joj.horse.schemas.user import UserBase


class RecordStatus(IntEnum):
    # waiting
    waiting = 0
    # working
    judging = 20
    # compiling = 21
    # fetched = 22
    # ignored = 30
    # done
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


class RecordCodeType(IntEnum):
    text = 0
    tar = 1
    zip = 2
    rar = 3


class RecordCase(BaseModel):
    class Config:
        orm_mode = True

    status: RecordStatus = RecordStatus.waiting
    score: int = 0
    time_ms: int = 0
    memory_kb: int = 0
    execute_status: int = 0
    stdout: str = ""
    stderr: str = ""


class Record(BaseODMSchema):
    status: RecordStatus = RecordStatus.waiting
    score: int = 0
    time_ms: int = 0
    memory_kb: int = 0
    domain: ReferenceSchema[Domain]
    problem: ReferenceSchema[Problem]
    problem_data: int = 0
    user: ReferenceSchema[UserBase]
    code_type: RecordCodeType
    code: PydanticObjectId
    judge_category: List[str]

    submit_at: datetime
    judge_at: Optional[datetime]

    judge_user: Optional[ReferenceSchema[UserBase]]

    compiler_texts: str = ""
    cases: List[RecordCase] = []

    _validate_domain: Callable[[AnyCallable], classmethod] = reference_schema_validator(
        "domain", Domain
    )
    _validate_user: Callable[[AnyCallable], classmethod] = reference_schema_validator(
        "user", UserBase
    )
    _validate_judge_user: Callable[
        [AnyCallable], classmethod
    ] = reference_schema_validator("judge_user", UserBase)
    _validate_problem: Callable[
        [AnyCallable], classmethod
    ] = reference_schema_validator("problem", Problem)


class ListRecords(BaseModel):
    results: List[Record]


class RecordCaseResult(BaseModel):
    index: int
    result: RecordCase


class RecordResult(BaseModel):
    status: RecordStatus
    score: int
    time_ms: int
    memory_kb: int
    judge_at: datetime
