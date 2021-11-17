from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy.schema import Column, ForeignKey, UniqueConstraint
from sqlmodel import Field, Relationship
from sqlmodel.sql.sqltypes import GUID

from joj.horse.models.base import ORMUtils

if TYPE_CHECKING:
    from joj.horse.models import Problem, ProblemSet


class ProblemProblemSetLink(ORMUtils, table=True):  # type: ignore[call-arg]
    __tablename__ = "problem_problem_set_links"
    __table_args__ = (UniqueConstraint("problem_set_id", "position"),)

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
    position: int = Field(..., nullable=False, sa_column_kwargs={"server_default": "0"})

    problem: "Problem" = Relationship(back_populates="problem_problem_set_links")
    problem_set: "ProblemSet" = Relationship(back_populates="problem_problem_set_links")
