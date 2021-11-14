from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlmodel import Field

from joj.horse.schemas import BaseModel
from joj.horse.schemas.base import (
    DomainMixin,
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

if TYPE_CHECKING:
    pass


class ProblemSetEdit(BaseModel):
    url: Optional[UserInputURL]
    title: Optional[NoneEmptyLongStr]
    content: Optional[LongText]
    hidden: Optional[bool]
    scoreboard_hidden: Optional[bool]
    available_time: Optional[datetime]
    due_time: Optional[datetime]


class ProblemSetBase(URLORMSchema):
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
        description="the problem set is available from",
    )
    due_time: datetime = Field(
        sa_column=get_datetime_column(index=False),
        description="the problem set is due at",
    )


class ProblemSetCreate(URLCreateMixin, ProblemSetBase):
    available_time: UTCDatetime = Field(default_factory=datetime.utcnow)
    due_time: UTCDatetime = Field(
        default_factory=lambda: datetime.utcnow() + timedelta(days=7)
    )


class ProblemSet(ProblemSetBase, DomainMixin, IDMixin):
    num_submit: int = Field(0, index=False, nullable=False)
    num_accept: int = Field(0, index=False, nullable=False)

    owner_id: UUID


class ProblemSetDetail(TimestampMixin, ProblemSet):
    pass
