from datetime import datetime
import re
from typing import Optional

from pydantic import validator, EmailStr
from pymongo import IndexModel, ASCENDING

from joj.horse.odm import Document, Reference

UID_RE = re.compile(r'-?\d+')
UNAME_RE = re.compile(r'[^\s\u3000](.{,254}[^\s\u3000])?')


class User(Document):
    class Mongo:
        collection = "users"
        indexes = [
            IndexModel([("scope", ASCENDING), ("uname_lower", ASCENDING)], unique=True),
            IndexModel([("scope", ASCENDING), ("mail_lower", ASCENDING)], unique=True),
        ]

    scope: str
    uname: str
    mail: EmailStr

    uname_lower: str = None
    mail_lower: str = None
    gravatar: str = None

    student_id: str = ''
    real_name: str = ''

    salt: str = ''
    hash: str = ''

    register_timestamp: datetime
    register_ip: str = "0.0.0.0"
    login_timestamp: datetime
    login_ip: str = "0.0.0.0"

    @validator("uname", pre=True)
    def validate_uname(cls, v: str):
        if not UNAME_RE.fullmatch(v):
            raise ValueError('uname')
        return v

    @validator("uname_lower", pre=True, always=True)
    def default_uname_lower(cls, v, *, values, **kwargs):
        return v or values["uname"].strip().lower()

    @validator("mail_lower", pre=True, always=True)
    def default_mail_lower(cls, v, *, values, **kwargs):
        return v or values["mail"].strip().lower()

    @validator("gravatar", pre=True, always=True)
    def default_gravatar(cls, v, *, values, **kwargs):
        return v or values["mail"].strip().lower()

    @validator("register_timestamp", pre=True, always=True)
    def default_register_timestamp(cls, v, *, values, **kwargs):
        return v or datetime.utcnow()

    @validator("login_timestamp", pre=True, always=True)
    def default_login_timestamp(cls, v, *, values, **kwargs):
        return v or datetime.utcnow()


class UserReference(Reference):
    data: Optional[User] = None
    reference = User


async def create(user: User) -> User:
    return await user.insert() and user or None


async def get_by_uname(scope: str, uname: str) -> User:
    return await User.find_one({'scope': scope, 'uname_lower': uname.strip().lower()})


async def login_by_jaccount(student_id: str, jaccount_name: str, real_name: str, ip: str) -> User:
    scope = "sjtu"
    user = await get_by_uname(scope=scope, uname=jaccount_name)
    if user:
        user.login_timestamp = datetime.utcnow()
        user.login_ip = ip
        await user.save()
    else:
        user = User(
            scope=scope,
            uname=jaccount_name,
            mail=EmailStr(jaccount_name + "@sjtu.edu.cn"),
            student_id=student_id,
            real_name=real_name,
            register_timestamp=datetime.utcnow(),
            register_ip=ip,
            login_timestamp=datetime.utcnow(),
            login_ip=ip,
        )
        user = await create(user=user)
    return user
