from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import event
from sqlalchemy.schema import Column, ForeignKey
from sqlmodel import Field, Relationship
from sqlmodel.sql.sqltypes import GUID

from joj.horse.models.base import DomainURLORMModel, url_pre_save
from joj.horse.models.link_tables import ProblemProblemSetLink
from joj.horse.schemas.problem_set import ProblemSetDetail

if TYPE_CHECKING:
    from joj.horse.models import Domain, Problem, User


class ProblemSet(DomainURLORMModel, ProblemSetDetail, table=True):  # type: ignore[call-arg]
    __tablename__ = "problem_sets"

    domain_id: UUID = Field(
        sa_column=Column(GUID, ForeignKey("domains.id", ondelete="CASCADE"))
    )
    domain: Optional["Domain"] = Relationship(back_populates="problem_sets")

    owner_id: UUID = Field(
        sa_column=Column(GUID, ForeignKey("users.id", ondelete="RESTRICT"))
    )
    owner: Optional["User"] = Relationship(back_populates="owned_problem_sets")

    problems: List["Problem"] = Relationship(
        back_populates="problem_sets", link_model=ProblemProblemSetLink
    )


event.listen(ProblemSet, "before_insert", url_pre_save)
event.listen(ProblemSet, "before_update", url_pre_save)
