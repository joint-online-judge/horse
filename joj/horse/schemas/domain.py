import string
from typing import Optional

from pydantic import Field, validator

from joj.horse.schemas.base import BaseModel, LongStr, LongText, UserInputURL


class DomainEdit(BaseModel):
    url: Optional[UserInputURL]
    name: Optional[LongStr]
    gravatar: Optional[LongStr]
    bulletin: Optional[LongText]


class DomainCreate(BaseModel):
    url: UserInputURL = Field("", description="(unique) url of the domain")
    name: LongStr = Field(..., description="displayed name of the domain")
    bulletin: LongText = Field("", description="bulletin of the domain")
    gravatar: LongStr = Field("", description="gravatar url of the domain")

    @validator("url")
    def validate_url(cls, v: str) -> str:
        for c in v:
            if c not in string.ascii_letters + string.digits + "_-":
                raise ValueError("url")
        return v


class DomainTransfer(BaseModel):
    target_user: str = Field(..., description="'me' or id of the user")


# class Domain(DomainCreate, BaseODMSchema):
#     url: NoneEmptyLongStr
#     owner: ReferenceSchema[UserBase]
#
#     _validate_owner: Callable[[AnyCallable], classmethod] = reference_schema_validator(
#         "owner", UserBase
#     )
