from uuid import UUID

from sqlmodel import Field

from joj.horse.schemas.base import BaseORMSchema, IDMixin, TimestampMixin


class UserAccessKey(BaseORMSchema, IDMixin):
    service: str = Field(index=False, nullable=False)
    access_key_id: str = Field(index=False, nullable=False)
    secret_access_key: str = Field(index=False, nullable=False)

    user_id: UUID


class UserAccessKeyDetail(TimestampMixin, UserAccessKey):
    pass
