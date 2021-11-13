from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlmodel import Field

from joj.horse.schemas.base import (
    BaseModel,
    IDMixin,
    LongStr,
    LongText,
    NoneEmptyLongStr,
    TimestampMixin,
    URLCreateMixin,
    URLORMSchema,
    UserInputURL,
)

if TYPE_CHECKING:
    pass


class DomainBase(URLORMSchema):
    name: NoneEmptyLongStr = Field(
        ...,
        nullable=False,
        description="displayed name of the domain",
    )
    gravatar: LongStr = Field(
        "", index=False, nullable=True, description="gravatar url of the domain"
    )
    bulletin: LongText = Field(
        "", index=False, nullable=True, description="bulletin of the domain"
    )
    hidden: bool = Field(
        True,
        index=False,
        nullable=False,
        description="is the domain hidden",
    )


class DomainCreate(URLCreateMixin, DomainBase):
    pass


class Domain(DomainBase, IDMixin):
    owner_id: UUID


class DomainEdit(BaseModel):
    url: Optional[UserInputURL]
    name: Optional[LongStr]
    gravatar: Optional[LongStr]
    bulletin: Optional[LongText]
    hidden: Optional[bool]


class DomainTransfer(BaseModel):
    target_user: str = Field(..., description="'me' or id of the user")


class DomainDetail(TimestampMixin, Domain):
    pass
