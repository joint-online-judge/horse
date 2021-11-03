from enum import IntEnum
from typing import List, Optional

# from joj.elephant.schemas import Config as ProblemConfig
from pydantic import Field

from joj.horse.schemas import BaseModel
from joj.horse.schemas.base import (  # NoneEmptyLongStr,
    LongText,
    NoneEmptyStr,
    UserInputURL,
)

# from joj.horse.schemas.problem_set import ProblemSet
# from joj.horse.schemas.user import UserBase

# from pydantic.typing import AnyCallable

# from joj.horse.schemas.domain import Domain
# from joj.horse.schemas.problem_group import ProblemGroup


class DataVersion(IntEnum):
    v1 = 1
    v2 = 2


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


#
# class Problem(BaseModel):
#     pass


# class Problem(ProblemCreate, BaseODMSchema):
#     domain: ReferenceSchema[Domain]
#     owner: ReferenceSchema[UserBase]
#     problem_group: ReferenceSchema[ProblemGroup]
#     # problem_set: ReferenceSchema[ProblemSet]
#
#     url: NoneEmptyLongStr
#     config: ProblemConfig = ProblemConfig()
#
#     num_submit: int = 0
#     num_accept: int = 0
#
#     data: Optional[int] = None  # modify later
#     total_score: int = 0
#     data_version: DataVersion = DataVersion.v2
#
#     _validate_domain: Callable[[AnyCallable], classmethod] = reference_schema_validator(
#         "domain", Domain
#     )
#     _validate_owner: Callable[[AnyCallable], classmethod] = reference_schema_validator(
#         "owner", UserBase
#     )
#     _validate_problem_group: Callable[
#         [AnyCallable], classmethod
#     ] = reference_schema_validator("problem_group", ProblemGroup)
#     # _validate_problem_set: Callable[
#     #     [AnyCallable], classmethod
#     # ] = reference_schema_validator("problem_set", ProblemSet)


class ProblemClone(BaseModel):
    problems: List[str]
    problem_set: str = Field(..., description="url or id of the problem set")
    new_group: bool = Field(False, description="whether to create new problem group")
