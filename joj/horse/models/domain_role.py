from datetime import datetime

from pydantic import validator
from pymongo import ASCENDING, IndexModel

from joj.horse.models.domain import DomainReference
from joj.horse.models.permission import DomainPermission
from joj.horse.odm import Document


class DomainRole(Document):
    class Mongo:
        collection = "domain.roles"
        indexes = [
            IndexModel("domain"),
            IndexModel("role"),
            IndexModel([("domain", ASCENDING), ("role", ASCENDING)], unique=True),
        ]

    permission: DomainPermission = DomainPermission()

    domain: DomainReference
    role: str
    updated_at: datetime

    @validator("updated_at", pre=True, always=True)
    def default_updated_at(cls, v, *, values, **kwargs):
        return v or datetime.utcnow()
