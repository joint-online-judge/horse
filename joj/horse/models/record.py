from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy.schema import Column, ForeignKey
from sqlmodel import Field, Relationship
from sqlmodel.sql.sqltypes import GUID

from joj.horse.models.base import BaseORMModel

if TYPE_CHECKING:
    from joj.horse.models import Problem, ProblemSet, User


class Record(BaseORMModel, table=True):  # type: ignore[call-arg]
    __tablename__ = "records"
    # __table_args__ = (UniqueConstraint("domain_id", "url"),)

    problem_set_id: Optional[UUID] = Field(
        sa_column=Column(
            GUID, ForeignKey("problem_sets.id", ondelete="SET NULL"), nullable=True
        )
    )
    problem_set: Optional["ProblemSet"] = Relationship(back_populates="records")

    problem_id: Optional[UUID] = Field(
        sa_column=Column(
            GUID, ForeignKey("problems.id", ondelete="SET NULL"), nullable=True
        )
    )
    problem: Optional["Problem"] = Relationship(back_populates="records")

    user_id: Optional[UUID] = Field(
        sa_column=Column(
            GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        )
    )
    user: Optional["User"] = Relationship(back_populates="records")
