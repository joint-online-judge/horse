from typing import TYPE_CHECKING, List, Optional
from uuid import UUID

from sqlalchemy import event
from sqlalchemy.schema import Column, ForeignKey
from sqlmodel import Field, Relationship
from sqlmodel.sql.sqltypes import GUID

from joj.horse.models.base import DomainURLORMModel, URLMixin, url_pre_save
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


class ProblemBase(URLMixin):
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


class ProblemCreate(ProblemBase):
    pass


class ProblemClone(BaseModel):
    problems: List[str]
    problem_set: str = Field(..., description="url or id of the problem set")
    new_group: bool = Field(False, description="whether to create new problem group")


class Problem(DomainURLORMModel, ProblemBase, table=True):  # type: ignore[call-arg]
    __tablename__ = "problems"

    num_submit: int = Field(0, index=False, nullable=False)
    num_accept: int = Field(0, index=False, nullable=False)
    data_version: int = Field(2, index=False, nullable=False)
    languages: str = Field("[]", index=False, nullable=False)

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


event.listen(Problem, "before_insert", url_pre_save)
event.listen(Problem, "before_update", url_pre_save)
