from datetime import datetime
from typing import Optional

from pydantic import EmailStr
from pymongo import ASCENDING, IndexModel
from umongo import fields
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument

from joj.horse.models.base import DocumentMixin
from joj.horse.schemas.user import User as UserSchema
from joj.horse.utils.db import instance


@instance.register
class User(DocumentMixin, MotorAsyncIODocument):
    class Meta:
        collection_name = "users"
        indexes = [
            IndexModel([("scope", ASCENDING), ("uname_lower", ASCENDING)], unique=True),
            IndexModel([("scope", ASCENDING), ("mail_lower", ASCENDING)], unique=True),
        ]
        strict = False

    scope = fields.StringField(required=True)
    uname = fields.StringField(required=True)
    mail = fields.EmailField(required=True)

    uname_lower = fields.StringField(required=True)
    mail_lower = fields.StringField(required=True)
    gravatar = fields.StringField(required=True)

    student_id = fields.StringField(default="")
    real_name = fields.StringField(default="")

    salt = fields.StringField(default="")
    hash = fields.StringField(default="")
    role = fields.StringField(default="user")

    register_timestamp = fields.DateTimeField(required=True)
    register_ip = fields.StringField(default="0.0.0.0")
    login_timestamp = fields.DateTimeField(required=True)
    login_ip = fields.StringField(default="0.0.0.0")

    @classmethod
    async def find_by_uname(cls, scope: str, uname: str) -> "User":
        return await cls.find_one(
            {"scope": scope, "uname_lower": uname.strip().lower()}
        )

    @classmethod
    async def login_by_jaccount(
        cls, student_id: str, jaccount_name: str, real_name: str, ip: str
    ) -> Optional["User"]:
        scope = "sjtu"
        user = await cls.find_by_uname(scope=scope, uname=jaccount_name)
        if user:
            user.login_timestamp = datetime.utcnow()
            user.login_ip = ip
            await user.commit()
        else:
            user_schema = UserSchema(
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
            user = User(**user_schema.to_model())
            if not await user.commit():
                return None
        return user
