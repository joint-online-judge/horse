from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import event
from sqlalchemy.schema import Column, ForeignKey
from sqlmodel import Field, Relationship
from sqlmodel.sql.sqltypes import GUID

from joj.horse.models.base import DomainURLORMModel, url_pre_save
from joj.horse.models.link_tables import ProblemProblemSetLink
from joj.horse.schemas.problem import ProblemDetail

if TYPE_CHECKING:
    from joj.horse.models import Domain, ProblemGroup, ProblemSet, User


class Problem(DomainURLORMModel, ProblemDetail, table=True):  # type: ignore[call-arg]
    __tablename__ = "problems"

    domain_id: UUID = Field(
        sa_column=Column(GUID, ForeignKey("domains.id", ondelete="CASCADE"))
    )
    domain: Optional["Domain"] = Relationship(back_populates="problems")

    owner_id: UUID = Field(
        sa_column=Column(GUID, ForeignKey("users.id", ondelete="RESTRICT"))
    )
    owner: Optional["User"] = Relationship(back_populates="owned_problems")

    problem_group_id: UUID = Field(
        sa_column=Column(GUID, ForeignKey("problem_groups.id", ondelete="RESTRICT"))
    )
    problem_group: Optional["ProblemGroup"] = Relationship(back_populates="problems")

    problem_sets: List["ProblemSet"] = Relationship(
        back_populates="problems", link_model=ProblemProblemSetLink
    )


event.listen(Problem, "before_insert", url_pre_save)
event.listen(Problem, "before_update", url_pre_save)
