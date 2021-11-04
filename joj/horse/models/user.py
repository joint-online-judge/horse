from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from pydantic import EmailStr, root_validator, validator
from sqlalchemy.sql.expression import Select
from sqlmodel import Field, Relationship
from uvicorn.config import logger

from joj.horse.models.base import BaseORMModel, SQLModel, get_datetime_column, utcnow
from joj.horse.models.permission import DefaultRole
from joj.horse.models.user_oauth_account import UserOAuthAccount
from joj.horse.utils.db import db_session
from joj.horse.utils.errors import BizError, ErrorCode

if TYPE_CHECKING:
    from joj.horse.models import Domain, DomainUser, Problem, ProblemSet
    from joj.horse.utils.auth import JWTAccessToken


class UserCreate(SQLModel):
    username: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    oauth_name: Optional[str] = None
    oauth_account_id: Optional[str] = None

    @validator("email", pre=True, always=True)
    def validate_email(cls, v: Any) -> Optional[EmailStr]:
        if not v:
            return None
        return EmailStr(v)


class UserBase(BaseORMModel):
    username: str = Field(index=False)
    email: EmailStr = Field(index=False)

    gravatar: str = Field(default="", index=False)
    student_id: str = Field(default="")
    real_name: str = Field(default="")
    role: str = Field(default=str(DefaultRole.USER))
    is_active: bool = Field(default=False, index=False)

    def find_domains(self, role: Optional[List[str]]) -> Select:
        from joj.horse import models

        statement = models.Domain.sql_select().outerjoin(models.DomainUser).distinct()
        # if user.role != "root":
        #     # root user can view all domains
        statement = statement.where(models.DomainUser.user_id == self.id)
        if role is not None:
            statement = statement.where(models.DomainUser.role.in_(role))
        return statement


class UserDetail(UserBase):
    # register_at = fields.DatetimeField(auto_now_add=True)
    register_ip: str = Field(default="0.0.0.0", index=False)
    login_at: datetime = Field(
        sa_column=get_datetime_column(index=False, server_default=utcnow())
    )
    login_ip: str = Field(default="0.0.0.0", index=False)


class User(UserDetail, table=True):  # type: ignore[call-arg]
    __tablename__ = "users"

    hashed_password: str = Field(default="", index=False)
    username_lower: str = Field(index=True, sa_column_kwargs={"unique": True})
    email_lower: EmailStr = Field(index=True, sa_column_kwargs={"unique": True})

    owned_domains: List["Domain"] = Relationship(back_populates="owner")
    domain_users: List["DomainUser"] = Relationship(back_populates="user")
    owned_problems: List["Problem"] = Relationship(back_populates="owner")
    owned_problem_sets: List["ProblemSet"] = Relationship(back_populates="owner")
    oauth_accounts: List["UserOAuthAccount"] = Relationship(back_populates="user")

    @root_validator(pre=True)
    def validate_lower_name(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if "username" not in values:
            raise ValueError("username undefined")
        values["username_lower"] = values["username"].lower()
        if "email" not in values:
            raise ValueError("email undefined")
        values["email_lower"] = values["email"].lower()
        return values

    @classmethod
    async def find_by_uname(cls, scope: str, uname: str) -> Optional["User"]:
        return await User.get_or_none(scope=scope, uname_lower=uname.strip().lower())

    @classmethod
    async def login_by_jaccount(
        cls, student_id: str, jaccount_name: str, real_name: str, ip: str
    ) -> Optional["User"]:
        scope = "sjtu"
        try:
            user = await cls.find_by_uname(scope=scope, uname=jaccount_name)
            if user:
                user.login_at = datetime.now(tz=timezone.utc)
                user.login_ip = ip
            else:
                user = User(
                    scope=scope,
                    uname=jaccount_name,
                    mail=EmailStr(jaccount_name + "@sjtu.edu.cn"),
                    student_id=student_id,
                    real_name=real_name,
                    register_ip=ip,
                    login_timestamp=datetime.now(tz=timezone.utc),
                    login_ip=ip,
                )
            await user.save_model()
            return user
        except Exception as e:
            logger.exception(e)
            return None

    @classmethod
    async def create(
        cls,
        user_create: UserCreate,
        jwt_access_token: Optional["JWTAccessToken"],
        register_ip: str,
    ) -> "User":
        username = user_create.username
        email = user_create.email
        if user_create.oauth_name:
            if (
                jwt_access_token is None
                or jwt_access_token.category != "oauth"
                or jwt_access_token.oauth_name != user_create.oauth_name
                or jwt_access_token.id != user_create.oauth_account_id
            ):
                raise BizError(ErrorCode.UserRegisterError, "oauth account not matched")
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
            if not user_create.email:
                email = oauth_account.account_email
            student_id = jwt_access_token.student_id
            real_name = jwt_access_token.real_name
            is_active = True

        else:
            oauth_account = None
            if not user_create.password:
                raise BizError(ErrorCode.UserRegisterError, "password not provided")
            if not user_create.username:
                raise BizError(ErrorCode.UserRegisterError, "username not provided")
            if not user_create.email:
                raise BizError(ErrorCode.UserRegisterError, "email not provided")
            student_id = ""
            real_name = ""
            is_active = False

        if user_create.password:
            from joj.horse.utils.auth import pwd_context

            hashed_password = pwd_context.hash(user_create.password)
        else:
            # register with oauth can omit password
            hashed_password = ""

        async with db_session() as session:
            user = User(
                username=username,
                email=email,
                student_id=student_id,
                real_name=real_name,
                is_active=is_active,
                hashed_password=hashed_password,
                register_ip=register_ip,
                login_ip=register_ip,
            )
            session.sync_session.add(user)
            if oauth_account:
                oauth_account.user_id = user.id
                session.sync_session.add(oauth_account)
            await session.commit()
            await session.refresh(user)
            return user
