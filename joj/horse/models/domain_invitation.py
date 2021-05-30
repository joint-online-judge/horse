from pymongo import ASCENDING, IndexModel
from umongo import fields
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument

from joj.horse.models.base import DocumentMixin
from joj.horse.models.domain import Domain
from joj.horse.utils.db import instance


@instance.register
class DomainInvitation(DocumentMixin, MotorAsyncIODocument):
    class Meta:
        collection_name = "domain.invitations"
        indexes = [
            IndexModel("domain"),
            IndexModel("code"),
            IndexModel([("domain", ASCENDING), ("code", ASCENDING)], unique=True),
        ]

    domain = fields.ReferenceField(Domain, required=True)
    code = fields.StringField(required=True)
    role = fields.StringField(required=True)

    expire_at = fields.DateTimeField(required=False)
