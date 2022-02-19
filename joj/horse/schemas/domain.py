from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlmodel import Field

from joj.horse.schemas.base import (
    BaseModel,
    EditMetaclass,
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
        index=True,
        nullable=False,
        description="displayed name of the domain",
    )
    gravatar: LongStr = Field(
        "",
        nullable=False,
        sa_column_kwargs={"server_default": ""},
        description="gravatar url of the domain",
    )
    bulletin: LongText = Field(
        "",
        nullable=False,
        sa_column_kwargs={"server_default": ""},
        description="bulletin of the domain",
    )
    hidden: bool = Field(
        True,
        nullable=False,
        sa_column_kwargs={"server_default": "true"},
        description="is the domain hidden",
    )
    tag: LongStr = Field(
        "",
        nullable=False,
        sa_column_kwargs={"server_default": ""},
        description="tag of the domain",
    )


class DomainCreate(URLCreateMixin, DomainBase):
    pass


class Domain(DomainBase, IDMixin):
    owner_id: Optional[UUID] = None


class DomainEdit(BaseModel, metaclass=EditMetaclass):
    url: Optional[UserInputURL]
    name: Optional[LongStr]
    gravatar: Optional[LongStr]
    bulletin: Optional[LongText]
    hidden: Optional[bool]
    tag: Optional[LongStr]


class DomainTransfer(BaseModel):
    target_user: str = Field(..., description="'me' or id of the user")


class DomainDetail(TimestampMixin, Domain):
    pass


class DomainTag(BaseModel):
    __root__: LongStr
