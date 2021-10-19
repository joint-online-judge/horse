from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy.schema import Column, ForeignKey
from sqlmodel import Field, Relationship
from sqlmodel.sql.sqltypes import GUID

from joj.horse.models.base import BaseORMModel, DomainURLMixin
from joj.horse.models.link_tables import ProblemProblemSetLink
from joj.horse.schemas import BaseModel
from joj.horse.schemas.base import LongText, NoneEmptyLongStr, UserInputURL

if TYPE_CHECKING:
    from joj.horse.models import Domain, Problem, User


class ProblemSetEdit(BaseModel):
    title: Optional[NoneEmptyLongStr]
    content: Optional[LongText]
    hidden: Optional[bool]
    scoreboard_hidden: Optional[bool]
    available_time: Optional[datetime]
    due_time: Optional[datetime]


class ProblemSetCreate(BaseModel):
    # domain: LongStr = Field(..., description="url or the id of the domain")
    url: UserInputURL = Field(
        "", description="(unique in domain) url of the problem set"
    )
    title: NoneEmptyLongStr = Field(..., description="title of the problem set")
    content: LongText = Field("", description="content of the problem set")
    hidden: bool = Field(False, description="whether the problem set is hidden")
    scoreboard_hidden: bool = Field(
        False, description="whether the scoreboard of the problem set is hidden"
    )
    available_time: datetime = Field(
        datetime.utcnow(), description="the problem set is available from"
    )
    due_time: datetime = Field(
        datetime.utcnow() + timedelta(days=7), description="the problem set is due at"
    )


class ProblemSet(DomainURLMixin, BaseORMModel, table=True):  # type: ignore[call-arg]
    __tablename__ = "problem_sets"

    title: str = Field(index=False)
    content: str = Field(index=False, default="")
    hidden: bool = Field(index=False, default=False)
    scoreboard_hidden = Field(index=False, default=False)

    available_time: datetime = Field(index=False)
    due_time: datetime = Field(index=False)
    num_submit: int = Field(index=False, default=0)
    num_accept: int = Field(index=False, default=0)

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
