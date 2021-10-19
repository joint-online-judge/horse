from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy.schema import Column, ForeignKey
from sqlmodel import Field, Relationship
from sqlmodel.sql.sqltypes import GUID

from joj.horse.models.base import BaseORMModel, DomainURLMixin
from joj.horse.models.link_tables import ProblemProblemSetLink
from joj.horse.schemas.base import BaseModel, LongText, NoneEmptyStr, UserInputURL

if TYPE_CHECKING:
    from joj.horse.models import Domain, ProblemGroup, ProblemSet, User


class ProblemEdit(BaseModel):
    url: Optional[UserInputURL]
    title: Optional[NoneEmptyStr]
    content: Optional[LongText]
    hidden: Optional[bool]
    # data: Optional[int]
    # data_version: Optional[DataVersion]
    # languages: Optional[List[LongStr]]


class ProblemCreate(BaseModel):
    url: UserInputURL = Field("", description="(unique in domain) url of the problem")
    title: NoneEmptyStr = Field(..., description="title of the problem")
    content: LongText = Field("", description="content of the problem")
    hidden: bool = Field(False, description="is the problem hidden")
    # this field can be induced from the config file
    # data_version: DataVersion = Field(DataVersion.v2)
    # languages: List[LongStr] = Field(
    #     [], description="acceptable language of the problem"
    # )
    # problem_set: LongStr = Field(..., description="problem set it belongs to")


class ProblemClone(BaseModel):
    problems: List[str]
    problem_set: str = Field(..., description="url or ObjectId of the problem set")
    new_group: bool = Field(False, description="whether to create new problem group")


class Problem(DomainURLMixin, BaseORMModel, table=True):  # type: ignore[call-arg]
    __tablename__ = "problems"

    title: str = Field(index=False)
    content: str = Field(index=False, default="")
    hidden: bool = Field(index=False, default=False)
    num_submit: int = Field(index=False, default=0)
    num_accept: int = Field(index=False, default=0)

    data_version: int = Field(index=False, default=2)
    languages: str = Field(index=False, default="[]")

    domain_id: UUID = Field(
        sa_column=Column(GUID, ForeignKey("domains.id", ondelete="CASCADE"))
    )
    domain: Optional["Domain"] = Relationship(back_populates="problems")

    owner_id: UUID = Field(
        sa_column=Column(GUID, ForeignKey("users.id", ondelete="RESTRICT"))
    )
    owner: Optional["User"] = Relationship(back_populates="owned_problems")

    problem_group_id: UUID = Field(
        sa_column=Column(GUID, ForeignKey("problem_groups.id", ondelete="RESTRICT"))
    )
    problem_group: Optional["ProblemGroup"] = Relationship(back_populates="problems")

    problem_sets: List["ProblemSet"] = Relationship(
        back_populates="problems", link_model=ProblemProblemSetLink
    )
