import re
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional, Union
from uuid import UUID

from pydantic import EmailStr, validator
from sqlmodel import Field, SQLModel

from joj.horse.models.permission import DefaultRole
from joj.horse.schemas.base import (
    BaseModel,
    BaseORMSchema,
    EditMetaclass,
    IDMixin,
    TimestampMixin,
    get_datetime_column,
    utcnow,
)

if TYPE_CHECKING:
    from joj.horse.models import DomainUser

UID_RE = re.compile(r"-?\d+")
UNAME_RE = re.compile(r"[^\s\u3000](.{,254}[^\s\u3000])?")


class UserResetPassword(BaseModel):
    current_password: str = ""
    new_password: str


class UserEdit(BaseModel, metaclass=EditMetaclass):
    gravatar: Optional[str] = None


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


class UserBase(BaseORMSchema):
    username: str = Field(nullable=False)
    gravatar: str = Field(
        "",
        nullable=False,
        sa_column_kwargs={"server_default": ""},
    )


class UserPreview(UserBase, IDMixin):
    pass


class User(UserBase, IDMixin):
    role: str = Field(
        default=str(DefaultRole.USER),
        index=True,
        nullable=False,
        sa_column_kwargs={"server_default": str(DefaultRole.USER)},
    )
    is_active: bool = Field(
        False,
        nullable=False,
        sa_column_kwargs={"server_default": "false"},
    )


class UserWithDomainRole(UserPreview):
    domain_id: Optional[UUID] = None
    domain_role: Optional[str] = None

    @classmethod
    def from_domain_user(
        cls,
        domain_user: Optional["DomainUser"],
        user: Union["User", Dict[str, Any]],
    ) -> "UserWithDomainRole":
        if domain_user is None:
            domain_id = None
            domain_role = None
        else:
            domain_id = domain_user.domain_id
            domain_role = domain_user.role
        if not isinstance(user, dict):
            user = user.dict()
        return cls(
            **user,
            domain_id=domain_id,
            domain_role=domain_role,
        )


class UserDetail(TimestampMixin, User):
    email: EmailStr = Field(nullable=False)
    student_id: str = Field(
        "",
        index=True,
        nullable=False,
        sa_column_kwargs={"server_default": ""},
    )
    real_name: str = Field(
        "",
        index=True,
        nullable=False,
        sa_column_kwargs={"server_default": ""},
    )
    register_ip: str = Field(
        nullable=False,
        sa_column_kwargs={"server_default": "127.0.0.1"},
    )
    login_at: datetime = Field(
        sa_column=get_datetime_column(nullable=False, server_default=utcnow()),
    )
    login_ip: str = Field(
        nullable=False,
        sa_column_kwargs={"server_default": "127.0.0.1"},
    )


class UserDetailWithDomainRole(UserDetail, UserWithDomainRole):
    ...
