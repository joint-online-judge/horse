from typing import TYPE_CHECKING
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
    owner_id: UUID | None = None


class DomainEdit(BaseModel, metaclass=EditMetaclass):
    url: UserInputURL | None
    name: LongStr | None
    gravatar: LongStr | None
    bulletin: LongText | None
    hidden: bool | None
    tag: LongStr | None


class DomainTransfer(BaseModel):
    target_user: str = Field(..., description="'me' or id of the user")


class DomainDetail(TimestampMixin, Domain):
    pass
