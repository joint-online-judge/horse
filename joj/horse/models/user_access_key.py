from typing import TYPE_CHECKING
from uuid import UUID

from lakefs_client.models import CredentialsWithSecret
from sqlalchemy.schema import Column, ForeignKey
from sqlmodel import Field, Relationship, UniqueConstraint
from sqlmodel.sql.sqltypes import GUID
from starlette.concurrency import run_in_threadpool

from joj.horse.models.base import BaseORMModel
from joj.horse.schemas.user_access_key import UserAccessKeyDetail
from joj.horse.services.lakefs import ensure_credentials, ensure_user
from joj.horse.utils.errors import BizError, ErrorCode

if TYPE_CHECKING:
    from joj.horse.models import User


class UserAccessKey(BaseORMModel, UserAccessKeyDetail, table=True):  # type: ignore[call-arg]
    __tablename__ = "user_access_keys"
    __table_args__ = (UniqueConstraint("service", "user_id"),)

    user_id: UUID = Field(
        sa_column=Column(
            GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
    )
    user: "User" = Relationship(back_populates="access_keys")

    @classmethod
    async def get_lakefs_access_key(cls, user: "User") -> "UserAccessKey":
        access_key = await cls.one_or_none(service="lakefs", user_id=user.id)
        access_key_id = access_key.access_key_id if access_key else None

        def sync_func() -> CredentialsWithSecret:
            ensure_user(user.username)
            return ensure_credentials(user.username, access_key_id)

        credentials = await run_in_threadpool(sync_func)

        if access_key is None and credentials is None:
            raise BizError(ErrorCode.Error)

        if access_key is not None and credentials is None:
            return access_key

        if access_key is None:
            access_key = cls(
                service="lakefs",
                access_key_id=credentials.access_key_id,
                secret_access_key=credentials.secret_access_key,
                user_id=user.id,
            )
        else:
            access_key.access_key_id = credentials.access_key_id
            access_key.secret_access_key = credentials.secret_access_key

        await access_key.save_model()
        return access_key
