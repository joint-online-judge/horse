import asyncio
from datetime import datetime
from typing import Optional, Type

import motor.motor_asyncio
from bson import ObjectId
from pydantic import BaseModel, EmailStr
from umongo import Document
from umongo.fields import DateTimeField, EmailField, StringField
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument, MotorAsyncIOInstance

instance = MotorAsyncIOInstance()


class PydanticObjectId(ObjectId):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not isinstance(v, ObjectId):
            raise TypeError("ObjectId required")
        return str(v)


@instance.register
class UserODM(Document):
    class Meta:
        collection_name = "users"

    scope = StringField(required=True)
    uname = StringField(required=True)
    mail = EmailField(required=True)

    uname_lower = StringField(required=True)
    mail_lower = StringField(required=True)
    gravatar = StringField(default="")

    student_id = StringField(default="")
    real_name = StringField(default="")

    salt = StringField(default="")
    hash = StringField(default="")
    role = StringField(default="user")

    register_timestamp = DateTimeField(required=True)
    register_ip = StringField(default="0.0.0.0")
    login_timestamp = DateTimeField(required=True)
    login_ip = StringField(default="0.0.0.0")


class User(BaseModel):
    id: Optional[PydanticObjectId] = None

    scope: str
    uname: str
    mail: EmailStr

    uname_lower: str = ""
    mail_lower: str = ""
    gravatar: str = ""

    student_id: str = ""
    real_name: str = ""

    salt: str = ""
    hash: str = ""
    role: str = "user"

    register_timestamp: datetime
    register_ip: str = "0.0.0.0"
    login_timestamp: datetime
    login_ip: str = "0.0.0.0"

    class Config:
        orm_mode = True


# UserODM: Type[MotorAsyncIODocument]


async def main():
    db = motor.motor_asyncio.AsyncIOMotorClient()["horse-production"]
    instance.set_db(db)

    # User.bind_odm(UserODM)
    # print(UserODM.collection)
    print(UserODM.find)

    async for user in UserODM.find():
        # user: UserODM
        await user.commit()
        # print(u.mongo())


if __name__ == "__main__":
    asyncio.run(main())
