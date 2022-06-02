import base64
from typing import TYPE_CHECKING, Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy.schema import Column, ForeignKey
from sqlmodel import Field, Relationship, select
from sqlmodel.sql.sqltypes import GUID

from joj.horse.models.base import BaseORMModel
from joj.horse.services.db import db_session
from joj.horse.services.oauth import OAuth2Profile

if TYPE_CHECKING:
    from joj.horse.models import User


class UserOAuthAccount(BaseORMModel, table=True):  # type: ignore[call-arg]
    __tablename__ = "user_oauth_accounts"

    oauth_name: str = Field()
    access_token: str = Field()
    refresh_token: Optional[str] = Field(None, nullable=True)
    expires_at: Optional[int] = Field(None, nullable=True)
    account_id: str = Field(index=True)
    account_name: Optional[str] = Field(None, index=True, nullable=True)
    account_email: str = Field(index=True)

    user_id: Optional[UUID] = Field(
        sa_column=Column(GUID, ForeignKey("users.id", ondelete="CASCADE"))
    )
    user: Optional["User"] = Relationship(back_populates="oauth_accounts")

    @staticmethod
    async def create_or_update(
        oauth_name: str, token: Dict[str, Any], profile: OAuth2Profile, register_ip: str
    ) -> "UserOAuthAccount":
        access_token = token["access_token"]
        refresh_token = token.get("refresh_token", None)
        expires_at = token.get("expires_at", None)
        async with db_session() as session:
            statement = (
                select(UserOAuthAccount)
                .where(UserOAuthAccount.oauth_name == oauth_name)
                .where(UserOAuthAccount.account_id == profile.account_id)
            )
            results = await session.exec(statement)
            oauth_account: Optional[UserOAuthAccount] = results.one_or_none()
            if oauth_account:
                oauth_account.access_token = access_token
                oauth_account.refresh_token = refresh_token
                oauth_account.expires_at = expires_at
                oauth_account.account_name = profile.account_name
            else:
                # create tmp user, waiting for /register
                from joj.horse.models import User

                username = f"{profile.oauth_name}-{profile.account_name}"
                if User.one_or_none(username=username):
                    username = base64.b64encode(uuid4().bytes).decode()
                # if the email is not unique, /callback will return 400
                user = User(
                    username=username,
                    email=profile.account_email,
                    gravatar=profile.account_email,
                    student_id=profile.student_id,
                    real_name=profile.real_name,
                    is_active=False,
                    hashed_password="",
                    register_ip=register_ip,
                    login_ip=register_ip,
                )
                session.sync_session.add(user)
                oauth_account = UserOAuthAccount(
                    oauth_name=oauth_name,
                    access_token=access_token,
                    refresh_token=refresh_token,
                    expires_at=expires_at,
                    account_id=profile.account_id,
                    account_name=profile.account_name,
                    account_email=profile.account_email,
                    user=user,
                )
            session.sync_session.add(oauth_account)
            await session.commit()
            await session.refresh(oauth_account)
        return oauth_account
