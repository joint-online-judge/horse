from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from pydantic import EmailStr, root_validator
from sqlalchemy.sql.expression import Select, or_
from sqlmodel import Field, Relationship

from joj.horse.models.base import BaseORMModel
from joj.horse.models.user_oauth_account import UserOAuthAccount
from joj.horse.schemas.user import UserChangeProfile, UserCreate, UserDetail
from joj.horse.services.db import db_session
from joj.horse.utils.errors import BizError, ErrorCode

if TYPE_CHECKING:
    from joj.horse.models import (
        Domain,
        DomainUser,
        Problem,
        ProblemConfig,
        ProblemSet,
        Record,
        UserAccessKey,
    )
    from joj.horse.schemas.auth import JWTAccessToken


class User(BaseORMModel, UserDetail, table=True):  # type: ignore[call-arg]
    __tablename__ = "users"

    hashed_password: str = Field(
        "",
        nullable=False,
        sa_column_kwargs={"server_default": ""},
    )
    username_lower: str = Field(
        index=True,
        nullable=False,
        sa_column_kwargs={"unique": True},
    )
    email_lower: EmailStr = Field(
        index=True,
        nullable=False,
        sa_column_kwargs={"unique": True},
    )

    oauth_accounts: List["UserOAuthAccount"] = Relationship(back_populates="user")
    access_keys: List["UserAccessKey"] = Relationship(back_populates="user")
    owned_domains: List["Domain"] = Relationship(back_populates="owner")
    domain_users: List["DomainUser"] = Relationship(back_populates="user")
    owned_problems: List["Problem"] = Relationship(back_populates="owner")
    owned_problem_sets: List["ProblemSet"] = Relationship(back_populates="owner")
    problem_configs: List["ProblemConfig"] = Relationship(back_populates="committer")
    committed_records: List["Record"] = Relationship(
        back_populates="committer",
        sa_relationship_kwargs={"foreign_keys": "[Record.committer_id]"},
    )
    judged_records: List["Record"] = Relationship(
        back_populates="judger",
        sa_relationship_kwargs={"foreign_keys": "[Record.judger_id]"},
    )

    @root_validator(pre=True)
    def validate_lower_name(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if "username" not in values:
            raise ValueError("username undefined")
        values["username_lower"] = values["username"].lower()
        if "email" not in values:
            raise ValueError("email undefined")
        values["email_lower"] = values["email"].lower()
        return values

    def verify_password(self, plain_password: str) -> bool:
        from joj.horse.schemas.auth import pwd_context

        return pwd_context.verify(plain_password, self.hashed_password)

    async def reset_password(self, current_password: str, new_password: str) -> None:
        if self.hashed_password:
            if not self.verify_password(current_password):
                raise BizError(ErrorCode.UsernamePasswordError, "incorrect password")
        self.hashed_password = self._generate_password_hash(new_password)
        await self.save_model()

    async def update_profile(self, profile_change: "UserChangeProfile") -> None:
        if not profile_change.real_name:
            raise BizError(ErrorCode.UserProfileError, "real name not provided")
        if not profile_change.gravatar:
            raise BizError(ErrorCode.UserProfileError, "gravatar not provided")
        self.real_name = profile_change.real_name
        self.gravatar = profile_change.gravatar
        await self.save_model()

    @classmethod
    def _generate_password_hash(cls, password: str) -> str:
        from joj.horse.schemas.auth import pwd_context

        return pwd_context.hash(password)

    @classmethod
    def _create_user(cls, user_create: "UserCreate", register_ip: str) -> "User":
        if not user_create.password:
            raise BizError(ErrorCode.UserRegisterError, "password not provided")
        if not user_create.username:
            raise BizError(ErrorCode.UserRegisterError, "username not provided")
        if not user_create.email:
            raise BizError(ErrorCode.UserRegisterError, "email not provided")
        hashed_password = cls._generate_password_hash(user_create.password)
        user = User(
            username=user_create.username,
            email=user_create.email,
            student_id="",
            real_name="",
            is_active=False,
            hashed_password=hashed_password,
            register_ip=register_ip,
            login_ip=register_ip,
        )
        return user

    @classmethod
    async def _create_user_by_oauth(
        cls,
        user_create: "UserCreate",
        jwt_access_token: "JWTAccessToken",
        register_ip: str,
    ) -> Tuple["User", "UserOAuthAccount"]:
        oauth_account = await UserOAuthAccount.get_or_none(
            oauth_name=jwt_access_token.oauth_name,
            account_id=jwt_access_token.id,
        )
        if oauth_account is None:
            raise BizError(ErrorCode.UserRegisterError, "oauth account not matched")
        if not user_create.username:
            if not oauth_account.account_name:
                raise BizError(ErrorCode.UserRegisterError, "username not provided")
            username = oauth_account.account_name
        else:
            username = user_create.username
        email = oauth_account.account_email
        if user_create.email and user_create.email != oauth_account.account_email:
            raise BizError(
                ErrorCode.UserRegisterError,
                "email must be same as the primary email of oauth account",
            )
        if user_create.password:
            hashed_password = cls._generate_password_hash(user_create.password)
        else:
            # register with oauth can omit password
            hashed_password = ""  # pragma: no cover
        user = User(
            username=username,
            email=email,
            student_id=jwt_access_token.student_id,
            real_name=jwt_access_token.real_name,
            is_active=True,
            hashed_password=hashed_password,
            register_ip=register_ip,
            login_ip=register_ip,
        )
        return user, oauth_account

    @classmethod
    async def create(
        cls,
        user_create: "UserCreate",
        jwt_access_token: Optional["JWTAccessToken"],
        register_ip: str,
    ) -> "User":
        oauth_account: Optional[UserOAuthAccount]
        if user_create.oauth_name:
            if (
                jwt_access_token is None
                or jwt_access_token.category != "oauth"
                or jwt_access_token.oauth_name != user_create.oauth_name
                or jwt_access_token.id != user_create.oauth_account_id
            ):
                raise BizError(ErrorCode.UserRegisterError, "oauth account not matched")
            user, oauth_account = await cls._create_user_by_oauth(
                user_create, jwt_access_token, register_ip
            )
        else:
            user = cls._create_user(user_create, register_ip)
            oauth_account = None

        async with db_session() as session:
            session.sync_session.add(user)
            if oauth_account:  # pragma: no cover
                oauth_account.user_id = user.id
                session.sync_session.add(oauth_account)
            await session.commit()
            await session.refresh(user)
            return user

    def find_domains_statement(self, role: Optional[List[str]]) -> Select:
        from joj.horse import models

        statement = models.Domain.sql_select().outerjoin(models.DomainUser).distinct()
        # if user.role != "root":
        #     # root user can view all domains
        statement = statement.where(models.DomainUser.user_id == self.id)
        if role is not None:
            statement = statement.where(models.DomainUser.role.in_(role))  # type: ignore[attr-defined]
        return statement

    @classmethod
    def apply_search(cls, statement: Select, query: str) -> Select:
        looking_for = f"%{query}%"
        statement = statement.where(
            or_(
                cls.username_lower.ilike(looking_for),  # type: ignore[attr-defined]
                cls.email_lower.ilike(looking_for),  # type: ignore[attr-defined]
                cls.student_id.ilike(looking_for),  # type: ignore[attr-defined]
                cls.real_name.ilike(looking_for),  # type: ignore[attr-defined]
            )
        )
        return statement

    @classmethod
    def find_users_statement(cls, query: str) -> Select:
        return cls.apply_search(cls.sql_select(), query)
