from datetime import datetime

from pydantic import validator
from pymongo import ASCENDING, IndexModel

from joj.horse.models.domain import DomainReference
from joj.horse.models.user import UserReference
from joj.horse.odm import Document


class DomainUser(Document):
    class Mongo:
        collection = "domain.users"
        indexes = [
            IndexModel("domain"),
            IndexModel("user"),
            IndexModel([("domain", ASCENDING), ("user", ASCENDING)], unique=True),
        ]

    domain: DomainReference
    user: UserReference
    role: str

    join_at: datetime

    @validator("join_at", pre=True, always=True)
    def default_join_at(cls, v, *, values, **kwargs):
        return v or datetime.utcnow()
