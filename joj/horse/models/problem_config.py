from typing import TYPE_CHECKING
from uuid import UUID

from joj.elephant.errors import ElephantError
from joj.elephant.manager import Manager
from lakefs_client.models import Commit
from uvicorn.config import logger

from joj.horse.models.base import BaseORMModel
from joj.horse.models.problem import Problem
from joj.horse.models.user import User
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.lakefs import LakeFSProblemConfig
from joj.horse.utils.tasks import run_task_in_executor


class ProblemConfig(BaseORMModel):
    # class Meta:
    #     table = "problem_configs"
    #
    # problem: fields.ForeignKeyRelation[Problem] = fields.ForeignKeyField(
    #     "models.Problem",
    #     related_name="configs",
    #     on_delete=fields.CASCADE,
    #     index=True,
    # )
    # commiter: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
    #     "models.User",
    #     related_name="config_commits",
    #     on_delete=fields.SET_NULL,
    #     null=True,
    #     index=True,
    # )
    #
    # ref = fields.CharField(max_length=64)
    # data = fields.JSONField()

    if TYPE_CHECKING:
        problem_id: UUID

    @classmethod
    async def make_commit(
        cls, problem: Problem, commiter: User, message: str
    ) -> "ProblemConfig":
        def sync_func() -> Commit:
            problem_config = LakeFSProblemConfig(problem)
            manager = Manager(logger, problem_config.storage)
            manager.validate_source()
            return problem_config.commit(message)

        try:
            commit_result = await run_task_in_executor(sync_func)
            result = await cls.create(
                problem=problem,
                commiter=commiter,
                ref=commit_result.id,
                data={},
            )
        except ElephantError as e:
            raise BizError(ErrorCode.ProblemConfigValidationError, e.message)
        return result
