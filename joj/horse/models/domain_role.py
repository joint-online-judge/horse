from datetime import datetime
from bson import ObjectId
from typing import Union
from pymongo import IndexModel, ASCENDING

from pydantic import validator, BaseModel

from joj.horse.odm import Document
from joj.horse.models.user import UserReference
from joj.horse.models.domain import DomainReference
from joj.horse.models.permission import Permission


class DomainRole(Document):
    class Mongo:
        collection = "domain.roles"
        indexes = [
            IndexModel("domain"),
            IndexModel("role"),
            IndexModel([("domain", ASCENDING), ("role", ASCENDING)], unique=True),
        ]

    permission: Permission = Permission()

    domain: DomainReference
    role: str
    updated_at: datetime

    @validator("updated_at", pre=True, always=True)
    def default_updated_at(cls, v, *, values, **kwargs):
        return v or datetime.utcnow()
