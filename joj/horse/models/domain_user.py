from pymongo import ASCENDING, IndexModel
from umongo import fields
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument

from joj.horse.models.domain import Domain
from joj.horse.models.user import User
from joj.horse.utils.db import instance


@instance.register
class DomainUser(MotorAsyncIODocument):
    class Meta:
        collection_name = "domain.users"
        indexes = [
            IndexModel("domain"),
            IndexModel("user"),
            IndexModel([("domain", ASCENDING), ("user", ASCENDING)], unique=True),
        ]

    domain = fields.ReferenceField(Domain, required=True)
    user = fields.ReferenceField(User, required=True)
    role = fields.StringField(required=True)
    join_at = fields.DateTimeField(required=True)
