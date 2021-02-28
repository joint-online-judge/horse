from bson import ObjectId
from pymongo import IndexModel
from umongo import fields
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument

from joj.horse.models.base import DocumentMixin
from joj.horse.models.user import User
from joj.horse.utils.db import instance
from joj.horse.utils.errors import DomainNotFoundError


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

    @classmethod
    async def find_by_url_or_id(cls, url_or_id: str) -> "Domain":
        try:
            _id = ObjectId(url_or_id)
            res = await cls.find_one({"_id": _id})
        except:
            res = await cls.find_one({"url": url_or_id})
            if res is None:
                raise DomainNotFoundError(url_or_id)
        return res
