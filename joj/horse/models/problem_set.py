from datetime import datetime, timedelta
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import event
from sqlalchemy.schema import Column, ForeignKey
from sqlmodel import Field, Relationship
from sqlmodel.sql.sqltypes import GUID

from joj.horse.models.base import (
    DomainURLORMModel,
    URLMixin,
    UTCDatetime,
    get_datetime_column,
    url_pre_save,
)
from joj.horse.models.link_tables import ProblemProblemSetLink
from joj.horse.schemas import BaseModel
from joj.horse.schemas.base import LongText, NoneEmptyLongStr, UserInputURL

if TYPE_CHECKING:
    from joj.horse.models import Domain, Problem, User


class ProblemSetEdit(BaseModel):
    url: Optional[UserInputURL]
    title: Optional[NoneEmptyLongStr]
    content: Optional[LongText]
    hidden: Optional[bool]
    scoreboard_hidden: Optional[bool]
    available_time: Optional[datetime]
    due_time: Optional[datetime]


class ProblemSetBase(URLMixin):
    title: NoneEmptyLongStr = Field(
        ..., index=False, nullable=False, description="title of the problem set"
    )
    content: LongText = Field(
        "", index=False, nullable=True, description="content of the problem set"
    )
    hidden: bool = Field(
        False,
        index=False,
        nullable=False,
        description="whether the problem set is hidden",
    )
    scoreboard_hidden: bool = Field(
        False,
        index=False,
        nullable=False,
        description="whether the scoreboard of the problem set is hidden",
    )
    available_time: datetime = Field(
        sa_column=get_datetime_column(index=False),
        default_factory=datetime.utcnow,
        description="the problem set is available from",
    )
    due_time: datetime = Field(
        sa_column=get_datetime_column(index=False),
        default_factory=lambda: datetime.utcnow() + timedelta(days=7),
        description="the problem set is due at",
    )


class ProblemSetCreate(ProblemSetBase):
    available_time: UTCDatetime
    due_time: UTCDatetime


class ProblemSet(DomainURLORMModel, ProblemSetBase, table=True):  # type: ignore[call-arg]
    __tablename__ = "problem_sets"

    num_submit: int = Field(0, index=False, nullable=False)
    num_accept: int = Field(0, index=False, nullable=False)

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
