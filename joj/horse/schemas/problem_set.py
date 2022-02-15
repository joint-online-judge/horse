from datetime import datetime
from typing import TYPE_CHECKING, List
from uuid import UUID

from sqlmodel import Field

from joj.horse.schemas import BaseModel
from joj.horse.schemas.base import (
    DomainMixin,
    EditMetaclass,
    IDMixin,
    LongText,
    NoneEmptyLongStr,
    TimestampMixin,
    URLCreateMixin,
    URLORMSchema,
    UserInputURL,
    UTCDatetime,
    get_datetime_column,
)
from joj.horse.schemas.problem import ProblemPreviewWithLatestRecord

if TYPE_CHECKING:
    pass


class ProblemSetUpdateProblem(BaseModel):
    position: int | None = Field(
        None,
        description="the position of the problem in the problem set. "
        "if None, append to the end of the problems list.",
    )


class ProblemSetAddProblem(ProblemSetUpdateProblem):
    problem: str = Field(..., description="url or id of the problem")


class ProblemSetEdit(BaseModel, metaclass=EditMetaclass):
    url: UserInputURL | None
    title: NoneEmptyLongStr | None
    content: LongText | None
    hidden: bool | None
    scoreboard_hidden: bool | None
    due_at: UTCDatetime | None
    lock_at: UTCDatetime | None
    unlock_at: UTCDatetime | None


class ProblemSetBase(URLORMSchema):
    title: NoneEmptyLongStr = Field(
        nullable=False,
        description="title of the problem set",
    )
    content: LongText = Field(
        "",
        nullable=False,
        sa_column_kwargs={"server_default": ""},
        description="content of the problem set",
    )
    hidden: bool = Field(
        False,
        nullable=False,
        sa_column_kwargs={"server_default": "false"},
        description="whether the problem set is hidden",
    )
    scoreboard_hidden: bool = Field(
        False,
        nullable=False,
        sa_column_kwargs={"server_default": "false"},
        description="whether the scoreboard of the problem set is hidden",
    )
    due_at: datetime | None = Field(
        None,
        sa_column=get_datetime_column(nullable=True),
        description="the problem set is due at this date",
    )
    lock_at: datetime | None = Field(
        None,
        sa_column=get_datetime_column(nullable=True),
        description="the problem set is locked after this date",
    )
    unlock_at: datetime | None = Field(
        None,
        sa_column=get_datetime_column(nullable=True),
        description="the problem set is unlocked after this date",
    )


class ProblemSetCreate(URLCreateMixin, ProblemSetBase):
    due_at: UTCDatetime | None = None
    lock_at: UTCDatetime | None = None
    unlock_at: UTCDatetime | None = None


class ProblemSet(ProblemSetBase, DomainMixin, IDMixin):
    num_submit: int = Field(0, nullable=False, sa_column_kwargs={"server_default": "0"})
    num_accept: int = Field(0, nullable=False, sa_column_kwargs={"server_default": "0"})

    owner_id: UUID | None = None


class ProblemSetDetail(TimestampMixin, ProblemSet):
    problems: List[ProblemPreviewWithLatestRecord] = []
