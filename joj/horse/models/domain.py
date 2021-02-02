from pymongo import IndexModel
from umongo import fields
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument

from joj.horse import models
from joj.horse.utils.db import instance


@instance.register
class Domain(MotorAsyncIODocument):
    class Meta:
        collection_name = "domains"
        indexes = [
            IndexModel("url", unique=True),
            IndexModel("owner"),
            IndexModel("name"),
        ]

    url = fields.StringField(required=True)
    name = fields.StringField(required=True)
    owner = fields.ReferenceField(models.User, required=True)

    gravatar = fields.StringField()
    bulletin = fields.StringField()
