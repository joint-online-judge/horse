from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlmodel import Field

from joj.horse.schemas.base import (
    BaseModel,
    DomainMixin,
    IDMixin,
    LongText,
    NoneEmptyStr,
    TimestampMixin,
    URLCreateMixin,
    URLORMSchema,
    UserInputURL,
)

if TYPE_CHECKING:
    pass


class ProblemEdit(BaseModel):
    url: Optional[UserInputURL]
    title: Optional[NoneEmptyStr]
    content: Optional[LongText]
    hidden: Optional[bool]
    # data: Optional[int]
    # data_version: Optional[DataVersion]
    # languages: Optional[List[LongStr]]


class ProblemBase(URLORMSchema):
    title: NoneEmptyStr = Field(
        ..., index=False, nullable=False, description="title of the problem"
    )
    content: LongText = Field(
        "", index=False, nullable=True, description="content of the problem"
    )
    hidden: bool = Field(
        False, index=False, nullable=False, description="is the problem hidden"
    )
    # this field can be induced from the config file
    # data_version: DataVersion = Field(DataVersion.v2)
    # languages: List[LongStr] = Field(
    #     [], description="acceptable language of the problem"
    # )
    # problem_set: LongStr = Field(..., description="problem set it belongs to")


class ProblemCreate(URLCreateMixin, ProblemBase):
    pass


class ProblemClone(BaseModel):
    problems: List[str]
    problem_set: str = Field(..., description="url or id of the problem set")
    new_group: bool = Field(False, description="whether to create new problem group")


class Problem(ProblemBase, DomainMixin, IDMixin):
    num_submit: int = Field(0, index=False, nullable=False)
    num_accept: int = Field(0, index=False, nullable=False)
    data_version: int = Field(2, index=False, nullable=False)
    languages: str = Field("[]", index=False, nullable=False)

    owner_id: UUID
    problem_group_id: UUID


class ProblemDetail(TimestampMixin, Problem):
    pass
