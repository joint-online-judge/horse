from bson import ObjectId
from pymongo import IndexModel
from umongo import fields
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument

from joj.horse.models.user import User
from joj.horse.utils.db import instance


class DocumentMixin:
    @classmethod
    async def find_by_id(cls, _id):
        return await cls.find_one({'_id': ObjectId(_id)})


@instance.register
class Domain(MotorAsyncIODocument, DocumentMixin):
    class Meta:
        collection_name = "domains"
        indexes = [
            IndexModel("url", unique=True),
            IndexModel("owner"),
            IndexModel("name"),
        ]

    # id = fields.ObjectIdField(attribute='_id')

    url = fields.StringField(required=True)
    name = fields.StringField(required=True)
    owner = fields.ReferenceField(User, required=True)

    gravatar = fields.StringField(default="")
    bulletin = fields.StringField(default="")

    @classmethod
    async def find_by_url_or_id(cls, url_or_id: str) -> 'Domain':
        try:
            _id = ObjectId(url_or_id)
            return await cls.find_one({'_id': ObjectId(_id)})
        except:
            return await cls.find_one({'url': url_or_id})
