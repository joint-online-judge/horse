from typing import TYPE_CHECKING, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import event
from sqlalchemy.schema import Column, ForeignKey
from sqlalchemy.sql.expression import Select
from sqlmodel import Field, Relationship, select
from sqlmodel.sql.sqltypes import GUID

from joj.horse.models.base import URLMixin, URLORMModel, url_pre_save
from joj.horse.schemas.base import (
    BaseModel,
    LongStr,
    LongText,
    NoneEmptyLongStr,
    UserInputURL,
)

if TYPE_CHECKING:
    from joj.horse.models import (
        DomainInvitation,
        DomainRole,
        DomainUser,
        Problem,
        ProblemGroup,
        ProblemSet,
        User,
    )
    from joj.horse.schemas.query import OrderingQuery, PaginationQuery


class DomainBase(URLMixin):
    name: NoneEmptyLongStr = Field(
        ...,
        nullable=False,
        description="displayed name of the domain",
    )
    gravatar: LongStr = Field(
        "", index=False, nullable=True, description="gravatar url of the domain"
    )
    bulletin: LongText = Field(
        "", index=False, nullable=True, description="bulletin of the domain"
    )
    hidden: bool = Field(
        True,
        index=False,
        nullable=False,
        description="is the domain hidden",
    )

    def find_domain_users_statement(self) -> Select:
        from joj.horse import models

        statement = (
            select(models.DomainUser, models.User)
            .where(models.DomainUser.domain_id == self.id)
            .where(models.DomainUser.user_id == models.User.id)
        )
        return statement


class DomainCreate(DomainBase):
    pass


class DomainEdit(BaseModel):
    url: Optional[UserInputURL]
    name: Optional[LongStr]
    gravatar: Optional[LongStr]
    bulletin: Optional[LongText]
    hidden: Optional[bool]


class DomainTransfer(BaseModel):
    target_user: str = Field(..., description="'me' or id of the user")


class Domain(URLORMModel, DomainBase, table=True):  # type: ignore[call-arg]
    __tablename__ = "domains"

    owner_id: UUID = Field(
        sa_column=Column(GUID, ForeignKey("users.id", ondelete="RESTRICT"))
    )
    owner: Optional["User"] = Relationship(back_populates="owned_domains")

    invitations: List["DomainInvitation"] = Relationship(back_populates="domain")
    roles: List["DomainRole"] = Relationship(back_populates="domain")
    users: List["DomainUser"] = Relationship(back_populates="domain")
    problems: List["Problem"] = Relationship(back_populates="domain")
    problem_sets: List["ProblemSet"] = Relationship(back_populates="domain")

    async def find_problems(
        self,
        include_hidden: bool = False,
        problem_set: Optional["ProblemSet"] = None,
        problem_group: Optional["ProblemGroup"] = None,
        ordering: Optional["OrderingQuery"] = None,
        pagination: Optional["PaginationQuery"] = None,
    ) -> Tuple[List["Problem"], int]:
        if problem_set:
            query_set = problem_set.problems.filter(domain=self)
        else:
            query_set = self.problems.all()  # type: ignore
        if not include_hidden:
            query_set = query_set.filter(hidden=False)
        if problem_group:
            query_set = query_set.filter(problem_group=problem_group)
        query_set = self.apply_ordering(query_set, ordering)
        count = await query_set.count()
        query_set = self.apply_pagination(query_set, pagination)
        problems = await query_set
        return problems, count


event.listen(Domain, "before_insert", url_pre_save)
event.listen(Domain, "before_update", url_pre_save)
