from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import event
from sqlalchemy.ext.orderinglist import ordering_list
from sqlalchemy.schema import Column, ForeignKey, UniqueConstraint
from sqlmodel import Field, Relationship
from sqlmodel.sql.sqltypes import GUID

from joj.horse.models.base import DomainURLORMModel, url_pre_save
from joj.horse.models.link_tables import ProblemProblemSetLink
from joj.horse.schemas.base import Operation
from joj.horse.schemas.problem_set import ProblemSetDetail
from joj.horse.utils.errors import BizError, ErrorCode

if TYPE_CHECKING:
    from joj.horse.models import Domain, Problem, User


class ProblemSet(DomainURLORMModel, ProblemSetDetail, table=True):  # type: ignore[call-arg]
    __tablename__ = "problem_sets"
    __table_args__ = (UniqueConstraint("domain_id", "url"),)

    domain_id: UUID = Field(
        sa_column=Column(
            GUID, ForeignKey("domains.id", ondelete="CASCADE"), nullable=False
        )
    )
    domain: "Domain" = Relationship(back_populates="problem_sets")

    owner_id: Optional[UUID] = Field(
        sa_column=Column(
            GUID,
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        )
    )
    owner: Optional["User"] = Relationship(back_populates="owned_problem_sets")

    # problems_link: List["Problem"] = Relationship(
    #     back_populates="problem_problem_set_links",
    #     # link_model=ProblemProblemSetLink,
    #     sa_relationship_kwargs={
    #         "secondary": ProblemProblemSetLink,
    #         "order_by": "ProblemProblemSetLink.position",
    #         "collection_class": ordering_list("position"),
    #     },
    # )

    # maintain the order of many to many relationship
    problem_problem_set_links: List[ProblemProblemSetLink] = Relationship(
        back_populates="problem_set",
        sa_relationship_kwargs={
            "order_by": "ProblemProblemSetLink.position",
            "collection_class": ordering_list("position"),
        },
    )

    problems: List["Problem"] = Relationship(
        back_populates="problem_sets",
        link_model=ProblemProblemSetLink,
        sa_relationship_kwargs={
            "order_by": "ProblemProblemSetLink.position",
        },
    )

    async def operate_problem(
        self, problem: "Problem", operation: Operation, position: Optional[int] = None
    ) -> None:
        assert problem.domain_id == self.domain_id
        link = await ProblemProblemSetLink.get_or_none(
            problem_set_id=self.id, problem_id=problem.id
        )
        if operation == Operation.Create:
            if link is not None:
                raise BizError(ErrorCode.IntegrityError, "problem already added")
            link = ProblemProblemSetLink(problem_set_id=self.id, problem_id=problem.id)
        else:
            if link is None:
                raise BizError(ErrorCode.IntegrityError, "problem not added")

        if operation == Operation.Read:
            return
        if operation in (Operation.Update, Operation.Delete):
            self.problem_problem_set_links.remove(link)
        if operation in (Operation.Create, Operation.Update):
            if position is None:
                self.problem_problem_set_links.append(link)
            else:
                self.problem_problem_set_links.insert(position, link)
        if operation == Operation.Delete:
            await link.delete_model(commit=False)
        await self.save_model()


event.listen(ProblemSet, "before_insert", url_pre_save)
event.listen(ProblemSet, "before_update", url_pre_save)
