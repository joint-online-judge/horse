from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import event
from sqlalchemy.orm import defer
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.sql.expression import Select, or_, true
from sqlmodel import Field, Relationship, select
from sqlmodel.sql.sqltypes import GUID

from joj.horse.models.base import URLORMModel, url_pre_save
from joj.horse.schemas.domain import DomainDetail

if TYPE_CHECKING:
    from joj.horse.models import (
        DomainInvitation,
        DomainRole,
        DomainUser,
        Problem,
        ProblemSet,
        User,
    )


class Domain(URLORMModel, DomainDetail, table=True):  # type: ignore[call-arg]
    __tablename__ = "domains"

    owner_id: UUID = Field(
        sa_column=Column(
            GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        )
    )
    owner: Optional["User"] = Relationship(back_populates="owned_domains")

    invitations: List["DomainInvitation"] = Relationship(back_populates="domain")
    roles: List["DomainRole"] = Relationship(back_populates="domain")
    users: List["DomainUser"] = Relationship(back_populates="domain")
    problems: List["Problem"] = Relationship(back_populates="domain")
    problem_sets: List["ProblemSet"] = Relationship(back_populates="domain")

    def find_problem_sets_statement(self, include_hidden: bool) -> Select:
        from joj.horse import models

        statement = select(models.ProblemSet).where(
            models.ProblemSet.domain_id == self.id
        )
        if not include_hidden:
            statement = statement.where(models.ProblemSet.hidden != true())
        return statement

    def find_problems_statement(self, include_hidden: bool) -> Select:
        from joj.horse import models

        statement = select(models.Problem).where(models.Problem.domain_id == self.id)
        if not include_hidden:
            statement = statement.where(models.Problem.hidden != true())
        return statement

    # async def find_problems(
    #     self,
    #     include_hidden: bool = False,
    #     problem_set: Optional["ProblemSet"] = None,
    #     problem_group: Optional["ProblemGroup"] = None,
    #     ordering: Optional["OrderingQuery"] = None,
    #     pagination: Optional["PaginationQuery"] = None,
    # ) -> Tuple[List["Problem"], int]:
    #     if problem_set:
    #         query_set = problem_set.problems.filter(domain=self)
    #     else:
    #         query_set = self.problems.all()  # type: ignore
    #     if not include_hidden:
    #         query_set = query_set.filter(hidden=False)
    #     if problem_group:
    #         query_set = query_set.filter(problem_group=problem_group)
    #     query_set = self.apply_ordering(query_set, ordering)
    #     count = await query_set.count()
    #     query_set = self.apply_pagination(query_set, pagination)
    #     problems = await query_set
    #     return problems, count

    def find_domain_users_statement(self) -> Select:
        from joj.horse import models

        statement = (
            select(models.DomainUser, models.User)
            .where(models.DomainUser.domain_id == self.id)
            .where(models.DomainUser.user_id == models.User.id)
        )
        return statement

    def find_domain_roles_statement(self) -> Select:
        from joj.horse import models

        statement = select(models.DomainRole).where(
            models.DomainRole.domain_id == self.id
        )
        return statement

    def find_domain_invitations_statement(self) -> Select:
        from joj.horse import models

        statement = select(models.DomainInvitation).where(
            models.DomainInvitation.domain_id == self.id
        )
        return statement

    def find_candidates_statement(self, query: str) -> Select:
        from joj.horse import models

        statement = select(models.User, models.DomainUser)
        statement = (
            models.User.apply_search(statement, query)
            .outerjoin_from(
                models.User,
                models.DomainUser,
                models.User.id == models.DomainUser.user_id,
            )
            .where(
                or_(
                    models.DomainUser.domain_id == self.id,
                    models.DomainUser.domain_id.is_(None),  # type: ignore[attr-defined]
                )
            )
        )
        return statement

    @classmethod
    def find_groups_statement(cls, query: str) -> Select:
        looking_for = f"%{query}%"
        statement = select(cls.group).where(cls.group.ilike(looking_for)).distinct()  # type: ignore[attr-defined]
        return statement

    def find_records_statement(
        self,
        problem_set_id: Optional[UUID],
        problem_id: Optional[UUID],
        submitter_id: Optional[UUID],
    ) -> Select:
        from joj.horse import models

        statement = select(models.Record).where(models.Record.domain_id == self.id)
        statement = statement.options(defer("cases"))  # exclude record.cases

        if problem_set_id:
            statement = statement.where(models.Record.problem_set_id == problem_set_id)
        if problem_id:
            statement = statement.where(models.Record.problem_id == problem_id)
        if submitter_id:
            statement = statement.where(models.Record.committer_id == submitter_id)
        return statement


event.listen(Domain, "before_insert", url_pre_save)
event.listen(Domain, "before_update", url_pre_save)
