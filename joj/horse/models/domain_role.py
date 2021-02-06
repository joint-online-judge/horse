from pymongo import ASCENDING, IndexModel
from umongo import EmbeddedDocument, fields
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument

from joj.horse.models.domain import Domain
from joj.horse.utils.db import instance


@instance.register
class Permission(EmbeddedDocument):
    pass


@instance.register
class DomainRole(MotorAsyncIODocument):
    class Meta:
        collection_name = "domain.roles"
        indexes = [
            IndexModel("domain"),
            IndexModel("role"),
            IndexModel([("domain", ASCENDING), ("role", ASCENDING)], unique=True),
        ]

    # permission: DomainPermission = DomainPermission()

    domain = fields.ReferenceField(Domain, required=True)
    role = fields.StringField(required=True)
    updated_at = fields.DateTimeField(required=True)

    # @validator("updated_at", pre=True, always=True)
    # def default_updated_at(cls, v, *, values, **kwargs):
    #     return v or datetime.utcnow()


DomainRole: MotorAsyncIODocument
