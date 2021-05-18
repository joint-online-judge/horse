from datetime import datetime
from typing import Any

from bson import ObjectId
from pymongo import IndexModel
from umongo import fields
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument

from joj.horse.models.base import DocumentMixin
from joj.horse.models.user import User
from joj.horse.utils.db import instance


@instance.register
class Domain(DocumentMixin, MotorAsyncIODocument):
    class Meta:
        collection_name = "domains"
        indexes = [
            IndexModel("url", unique=True),
            IndexModel("owner"),
            IndexModel("name"),
        ]

    url = fields.StringField(required=True)
    name = fields.StringField(required=True)
    owner = fields.ReferenceField(User, required=True)

    gravatar = fields.StringField(default="")
    bulletin = fields.StringField(default="")

    invitation_code = fields.StringField(default="")
    invitation_expire_at = fields.DateTimeField(default=datetime(1970, 1, 1))

    @classmethod
    async def find_by_url_or_id(cls: MotorAsyncIODocument, url_or_id: str) -> Any:
        if ObjectId.is_valid(url_or_id):
            filter = {"_id": ObjectId(url_or_id)}
        else:
            filter = {"url": url_or_id}
        return await cls.find_one(filter)
