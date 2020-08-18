from datetime import datetime
import re

from pydantic import validator, EmailStr
from motor.motor_asyncio import AsyncIOMotorClient
from joj.horse.odm import Document
from pymongo import IndexModel

UID_RE = re.compile(r'-?\d+')
UNAME_RE = re.compile(r'[^\s\u3000](.{,254}[^\s\u3000])?')

class User(Document):
    class Mongo:
        collection = "users"
        indexes = [
            IndexModel("uname", unique=True),
            IndexModel("mail", unique=True),
        ]

    uname: str
    mail: EmailStr

    student_id: int = 0
    real_name: str = ''

    salt: str = ''
    hash: str = ''

    register_timestamp: datetime
    register_ip: str
    login_timestamp: datetime
    login_ip: str

    gravatar: str = None

    @validator("uname")
    def validate_uname(cls, v: str):
        if not UNAME_RE.fullmatch(v):
            raise ValueError('uname')
        return v.lower()

    @validator("mail")
    def validate_mail(cls, v: str):
        return v.lower()

    @validator("gravatar", pre=True, always=True)
    def default_gravatar(cls, v, *, values, **kwargs):
        return v or values["mail"]


# async def create(user: User):
