from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from pydantic import EmailStr, root_validator
from sqlmodel import Field, Relationship
from tortoise import timezone
from uvicorn.config import logger

from joj.horse.models.base import BaseORMModel, utcnow
from joj.horse.models.permission import DefaultRole

if TYPE_CHECKING:
    from joj.horse.models import (
        Domain,
        DomainUser,
        Problem,
        ProblemSet,
        UserOAuthAccount,
    )
    from joj.horse.schemas.query import OrderingQuery, PaginationQuery


class UserBase(BaseORMModel):
    user_name: str = Field(index=False)
    email: EmailStr = Field(index=False)

    gravatar: str = Field(default="", index=False)
    student_id: str = Field(default="")
    real_name: str = Field(default="")


class User(UserBase, table=True):  # type: ignore[call-arg]
    __tablename__ = "users"

    salt: str = Field(default="", index=False)
    hash: str = Field(default="", index=False)
    role: str = Field(default=str(DefaultRole.USER))

    user_name_lower: str = Field(index=True, sa_column_kwargs={"unique": True})
    email_lower: EmailStr = Field(index=True, sa_column_kwargs={"unique": True})

    # register_at = fields.DatetimeField(auto_now_add=True)
    register_ip: str = Field(default="0.0.0.0", index=False)
    login_at: datetime = Field(
        sa_column_kwargs={"server_default": utcnow()}, index=False
    )
    login_ip: str = Field(default="0.0.0.0", index=False)

    owned_domains: List["Domain"] = Relationship(back_populates="owner")
    domain_users: List["DomainUser"] = Relationship(back_populates="user")
    owned_problems: List["Problem"] = Relationship(back_populates="owner")
    owned_problem_sets: List["ProblemSet"] = Relationship(back_populates="owner")
    oauth_accounts: List["UserOAuthAccount"] = Relationship(back_populates="user")

    @root_validator(pre=True)
    def validate_lower_name(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if "user_name" not in values:
            raise ValueError("user_name undefined")
        values["user_name_lower"] = values["user_name"].lower()
        if "email" not in values:
            raise ValueError("email undefined")
        values["email_lower"] = values["email"].lower()
        if "gravatar" not in values or not values["gravatar"]:
            values["gravatar"] = values["user_name_lower"]
        return values

    @classmethod
    async def find_by_uname(cls, scope: str, uname: str) -> Optional["User"]:
        return await User.get_or_none(scope=scope, uname_lower=uname.strip().lower())

    async def find_domains(
        self,
        role: Optional[List[str]],
        ordering: Optional["OrderingQuery"] = None,
        pagination: Optional["PaginationQuery"] = None,
    ) -> Tuple[List["Domain"], int]:
        if self.role != "root":
            # TODO: root user can view all domains
            pass
        query_set = self.domains.all()
        if role is not None:
            query_set = query_set.filter(role__in=role)
        query_set = query_set.select_related("domain", "domain__owner")
        query_set = self.apply_ordering(query_set, ordering, prefix="domain__")
        count = await query_set.count()
        query_set = self.apply_pagination(query_set, pagination)
        domain_users = await query_set
        domains = [domain_user.domain for domain_user in domain_users]
        return domains, count

    @classmethod
    async def login_by_jaccount(
        cls, student_id: str, jaccount_name: str, real_name: str, ip: str
    ) -> Optional["User"]:
        scope = "sjtu"
        try:
            user = await cls.find_by_uname(scope=scope, uname=jaccount_name)
            if user:
                user.login_at = timezone.now()
                user.login_ip = ip
            else:
                user = User(
                    scope=scope,
                    uname=jaccount_name,
                    mail=EmailStr(jaccount_name + "@sjtu.edu.cn"),
                    student_id=student_id,
                    real_name=real_name,
                    register_ip=ip,
                    login_timestamp=timezone.now(),
                    login_ip=ip,
                )
            await user.save()
            return user
        except Exception as e:
            logger.exception(e)
            return None
