from typing import TYPE_CHECKING, List, Optional
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
from joj.horse.schemas.record import RecordCodeType

if TYPE_CHECKING:
    pass


class ProblemEdit(BaseModel, metaclass=EditMetaclass):
    url: Optional[UserInputURL]
    title: Optional[NoneEmptyStr]
    content: Optional[LongText]
    hidden: Optional[bool]


class ProblemBase(URLORMSchema):
    title: NoneEmptyStr = Field(
        index=False,
        nullable=False,
        description="title of the problem",
    )
    content: LongText = Field(
        "",
        index=False,
        nullable=False,
        sa_column_kwargs={"server_default": ""},
        description="content of the problem",
    )
    hidden: bool = Field(
        False,
        index=False,
        nullable=False,
        sa_column_kwargs={"server_default": "false"},
        description="is the problem hidden",
    )


class ProblemCreate(URLCreateMixin, ProblemBase):
    pass


class ProblemClone(BaseModel):
    problems: List[str]
    problem_set: str = Field(..., description="url or id of the problem set")
    new_group: bool = Field(False, description="whether to create new problem group")


class ProblemPreview(ProblemBase, IDMixin):
    owner_id: UUID


class Problem(ProblemBase, DomainMixin, IDMixin):
    num_submit: int = Field(
        0, index=False, nullable=False, sa_column_kwargs={"server_default": "0"}
    )
    num_accept: int = Field(
        0, index=False, nullable=False, sa_column_kwargs={"server_default": "0"}
    )

    owner_id: Optional[UUID] = None
    problem_group_id: Optional[UUID] = None


class ProblemDetail(TimestampMixin, Problem):
    pass


class ProblemSolutionSubmit(BaseModel, metaclass=FormMetaclass):
    code_type: RecordCodeType
    file: Optional[UploadFile]
