from pymongo import ASCENDING, IndexModel
from umongo import fields
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument

from joj.horse.models.base import DocumentMixin
from joj.horse.models.domain import Domain
from joj.horse.models.user import User
from joj.horse.utils.db import instance


@instance.register
class DomainUser(MotorAsyncIODocument, DocumentMixin):
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
