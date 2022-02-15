from typing import TYPE_CHECKING, List, TypeVar
from uuid import UUID

from fastapi import UploadFile
from sqlmodel import Field

from joj.horse.schemas.base import (
    BaseModel,
    DomainMixin,
    EditMetaclass,
    FormMetaclass,
    IDMixin,
    LongText,
    NoneEmptyStr,
    TimestampMixin,
    URLCreateMixin,
    URLORMSchema,
    UserInputURL,
)
from joj.horse.schemas.record import RecordCodeType, RecordPreview

if TYPE_CHECKING:
    pass


class ProblemEdit(BaseModel, metaclass=EditMetaclass):
    url: UserInputURL | None
    title: NoneEmptyStr | None
    content: LongText | None
    hidden: bool | None


class ProblemBase(URLORMSchema):
    title: NoneEmptyStr = Field(
        nullable=False,
        description="title of the problem",
    )
    hidden: bool = Field(
        False,
        nullable=False,
        sa_column_kwargs={"server_default": "false"},
        description="is the problem hidden",
    )


class ProblemContentMixin(BaseModel):
    content: LongText = Field(
        "",
        nullable=False,
        sa_column_kwargs={"server_default": ""},
        description="content of the problem",
    )


class ProblemCreate(ProblemContentMixin, URLCreateMixin, ProblemBase):
    pass


class ProblemClone(BaseModel):
    from_domain: str = Field(..., description="url or id of the domain to clone from")
    problems: List[str]
    new_group: bool = Field(False, description="whether to create new problem group")


class ProblemPreview(ProblemBase, IDMixin):
    owner_id: UUID | None = None


class Problem(ProblemBase, DomainMixin, IDMixin):
    num_submit: int = Field(0, nullable=False, sa_column_kwargs={"server_default": "0"})
    num_accept: int = Field(0, nullable=False, sa_column_kwargs={"server_default": "0"})

    owner_id: UUID | None = None
    problem_group_id: UUID | None = None


class ProblemDetail(TimestampMixin, ProblemContentMixin, Problem):
    pass


class LatestRecordMixin(BaseModel):
    latest_record: RecordPreview | None


class ProblemPreviewWithLatestRecord(LatestRecordMixin, ProblemPreview):
    pass


class ProblemWithLatestRecord(LatestRecordMixin, Problem):
    pass


class ProblemDetailWithLatestRecord(LatestRecordMixin, ProblemDetail):
    pass


WithLatestRecordType = TypeVar("WithLatestRecordType", bound=LatestRecordMixin)


class ProblemSolutionSubmit(BaseModel, metaclass=FormMetaclass):
    code_type: RecordCodeType
    file: UploadFile | None
