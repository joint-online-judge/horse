from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy.sql.expression import Select
from sqlmodel import Field, select

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

    def find_domain_users_statement(self) -> Select:
        from joj.horse import models

        statement = (
            select(models.DomainUser, models.User)
            .where(models.DomainUser.domain_id == self.id)
            .where(models.DomainUser.user_id == models.User.id)
        )
        return statement


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
