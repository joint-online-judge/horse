import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, validator

from joj.horse.schemas.base import PydanticObjectId

UID_RE = re.compile(r'-?\d+')
UNAME_RE = re.compile(r'[^\s\u3000](.{,254}[^\s\u3000])?')


class UserBase(BaseModel):
    class Config:
        orm_mode = True

    id: Optional[PydanticObjectId]

    scope: str
    uname: str
    mail: EmailStr

    uname_lower: str = None
    mail_lower: str = None
    gravatar: str = None

    student_id: str = ''
    real_name: str = ''

    register_timestamp: datetime
    login_timestamp: datetime

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


class User(UserBase):
    salt: str = ''
    hash: str = ''
    role: str = 'user'

    register_ip: str = "0.0.0.0"
    login_ip: str = "0.0.0.0"
