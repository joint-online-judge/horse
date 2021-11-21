from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from joj.elephant.errors import ElephantError
from joj.elephant.manager import Manager
from lakefs_client.models import Commit
from sqlalchemy.schema import Column, ForeignKey
from sqlmodel import Field, Relationship
from sqlmodel.sql.sqltypes import GUID
from starlette.concurrency import run_in_threadpool
from uvicorn.config import logger

from joj.horse.models.base import BaseORMModel
from joj.horse.schemas.problem_config import ProblemConfigDetail
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.lakefs import LakeFSProblemConfig

if TYPE_CHECKING:
    from joj.horse.models import Problem, Record, User


class ProblemConfig(BaseORMModel, ProblemConfigDetail, table=True):  # type: ignore[call-arg]
    __tablename__ = "problem_configs"

    problem_id: Optional[UUID] = Field(
        sa_column=Column(
            GUID, ForeignKey("problems.id", ondelete="SET NULL"), nullable=True
        )
    )
    problem: Optional["Problem"] = Relationship(back_populates="problem_configs")

    author_id: Optional[UUID] = Field(
        sa_column=Column(
            GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        )
    )
    author: Optional["User"] = Relationship(back_populates="problem_configs")

    records: List["Record"] = Relationship(back_populates="problem_config")

    @classmethod
    async def make_commit(
        cls, problem: "Problem", author: "User", message: str
    ) -> "ProblemConfig":
        def sync_func() -> Commit:
            lakefs_problem_config = LakeFSProblemConfig(problem)
            manager = Manager(logger, lakefs_problem_config.storage)
            manager.validate_source()
            return lakefs_problem_config.commit(message)

        try:
            commit_result = await run_in_threadpool(sync_func)
            problem_config = cls(
                problem_id=problem.id,
                author_id=author.id,
                commit_id=commit_result.id,
            )
            await problem_config.save_model()
        except ElephantError as e:
            raise BizError(ErrorCode.ProblemConfigValidationError, e.message)
        return problem_config
