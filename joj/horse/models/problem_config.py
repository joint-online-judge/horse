from pathlib import Path
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

import orjson

# from joj.elephant.manager import Manager
from lakefs_client.models import Commit
from sqlalchemy.schema import Column, ForeignKey
from sqlmodel import Field, Relationship
from sqlmodel.sql.sqltypes import GUID
from starlette.concurrency import run_in_threadpool

from joj.elephant.errors import ElephantError
from joj.horse.models.base import BaseORMModel
from joj.horse.schemas.problem_config import ProblemConfigCommit, ProblemConfigDetail
from joj.horse.services.lakefs import LakeFSProblemConfig
from joj.horse.utils.errors import BizError, ErrorCode

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

    committer_id: Optional[UUID] = Field(
        sa_column=Column(
            GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        )
    )
    committer: Optional["User"] = Relationship(back_populates="problem_configs")

    records: List["Record"] = Relationship(back_populates="problem_config")

    @classmethod
    async def make_commit(
        cls, problem: "Problem", committer: "User", commit: ProblemConfigCommit
    ) -> "ProblemConfig":
        def sync_func() -> Commit:
            lakefs_problem_config = LakeFSProblemConfig(problem)
            # manager = Manager(logger, lakefs_problem_config.storage)
            # manager.validate_source()
            return lakefs_problem_config.commit(commit.message)

        try:
            commit_result = await run_in_threadpool(sync_func)
            lakefs_problem_config = LakeFSProblemConfig(problem)
            config_file = lakefs_problem_config.download_file(Path("config.json"))
            config_dict = orjson.loads(config_file.read())
            languages = []
            if isinstance(config_dict, dict) and "languages" in config_dict:
                languages = config_dict["languages"]
            problem_config = cls(
                problem_id=problem.id,
                committer_id=committer.id,
                commit_id=commit_result.id,
                languages=languages,
            )
            await problem_config.save_model()
        except ElephantError as e:
            raise BizError(ErrorCode.FileValidationError, e.message)
        return problem_config
