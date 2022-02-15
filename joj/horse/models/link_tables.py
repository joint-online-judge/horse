from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.orm import joinedload
from sqlalchemy.schema import Column, ForeignKey
from sqlmodel import Field, Relationship
from sqlmodel.sql.sqltypes import GUID

from joj.horse.models.base import ORMUtils
from joj.horse.utils.base import is_uuid

if TYPE_CHECKING:
    from joj.horse.models import Problem, ProblemSet


class ProblemProblemSetLink(ORMUtils, table=True):  # type: ignore[call-arg]
    __tablename__ = "problem_problem_set_links"

    problem_id: UUID = Field(
        sa_column=Column(
            GUID, ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True
        ),
    )
    problem_set_id: UUID = Field(
        sa_column=Column(
            GUID, ForeignKey("problem_sets.id", ondelete="CASCADE"), primary_key=True
        ),
    )
    position: int = Field(
        index=True, nullable=False, sa_column_kwargs={"server_default": "0"}
    )

    problem: "Problem" = Relationship(back_populates="problem_problem_set_links")
    problem_set: "ProblemSet" = Relationship(back_populates="problem_problem_set_links")

    @classmethod
    async def find_by_problem_set_and_problem(
        cls, problem_set: str, problem: str
    ) -> "ProblemProblemSetLink" | None:
        # this is buggy, do not use!
        # not sure how much it's better than three queries (maybe even worse)

        from joj.horse import models

        statement = cls.sql_select().options(
            joinedload(cls.problem_set, innerjoin=True),
            joinedload(cls.problem, innerjoin=True),
        )
        if is_uuid(problem_set):
            statement = statement.where(cls.problem_set_id == problem_set)
        else:
            statement = statement.where(models.ProblemSet.url == problem_set)
        if is_uuid(problem):
            statement = statement.where(cls.problem_id == problem)
        else:
            statement = statement.where(models.Problem.url == problem)
        from loguru import logger

        logger.info(statement)
        result = await cls.session_exec(statement)
        logger.info(result.all())
        return result.one_or_none()
