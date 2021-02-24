from pymongo import ASCENDING, IndexModel
from umongo import fields
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument

from joj.horse.models.base import DocumentMixin
from joj.horse.models.domain import Domain
from joj.horse.models.permission import DomainPermission
from joj.horse.utils.db import instance


@instance.register
class DomainRole(MotorAsyncIODocument, DocumentMixin):
    class Meta:
        collection_name = "domain.roles"
        indexes = [
            IndexModel("domain"),
            IndexModel("role"),
            IndexModel([("domain", ASCENDING), ("role", ASCENDING)], unique=True),
        ]

    domain = fields.ReferenceField(Domain, required=True)
    role = fields.StringField(required=True)
    permission = fields.EmbeddedField(DomainPermission, default=DomainPermission())

    updated_at = fields.DateTimeField(required=True)
