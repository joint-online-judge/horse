from datetime import datetime
from enum import IntEnum
from typing import List, Optional

from pydantic import BaseModel
from pymongo import ASCENDING, DESCENDING, IndexModel

from joj.horse.models.domain import DomainReference
from joj.horse.models.problem import ProblemReference
from joj.horse.models.problem_set import ProblemSetReference
from joj.horse.models.user import UserReference
from joj.horse.odm import Document


class RecordStatus(IntEnum):
    waiting = 0
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
    judging = 20
    compiling = 21
    fetched = 22
    ignored = 30


class RecordCodeType(IntEnum):
    text = 0
    tar = 1
    zip = 2
    rar = 3


class RecordCase(BaseModel):
    status: RecordStatus
    score: int = 0
    time_ms: int = 0
    memory_kb: int = 0
    execute_status: int = 0
    stdout: str = ""
    stderr: str = ""


class Record(Document):
    class Mongo:
        collection = "records"
        indexes = [
            IndexModel([("domain", ASCENDING), ("problem", ASCENDING), ("user", ASCENDING), ("submit_at", DESCENDING)]),
            IndexModel([("problem", ASCENDING), ("user", ASCENDING), ("submit_at", DESCENDING)]),
            IndexModel([("domain", ASCENDING), ("user", ASCENDING), ("submit_at", DESCENDING)]),
            IndexModel([("user", ASCENDING), ("submit_at", DESCENDING)]),
        ]

    status: RecordStatus
    score: int = 0
    time_ms: int = 0
    memory_kb: int = 0
    domain: DomainReference
    problem: ProblemReference
    problem_set: Optional[ProblemSetReference] = None  # modify later
    problem_data: int  # modify later
    user: UserReference
    code_type: RecordCodeType
    code: str  # modify later
    judge_category: List[str]

    submit_at: datetime
    judge_at: datetime

    judge_user: UserReference

    compiler_texts: str = ""
    cases: List[RecordCase] = []
