from typing import List, Optional

from bson import ObjectId
from pymongo import ASCENDING, IndexModel
from umongo import fields
from umongo.frameworks.motor_asyncio import AsyncIOMotorCursor, MotorAsyncIODocument

from joj.horse.models.base import DocumentMixin
from joj.horse.models.domain import Domain
from joj.horse.models.user import User
from joj.horse.schemas.query import BaseQuery
from joj.horse.utils.db import instance


@instance.register
class DomainUser(DocumentMixin, MotorAsyncIODocument):
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

    @classmethod
    def cursor_find_user_domains(
        cls, user_id: ObjectId, role: List[str], query: Optional[BaseQuery] = None
    ) -> AsyncIOMotorCursor:
        condition = {"user": user_id}
        if len(role) > 0:
            condition["role"] = {"$in": role}
        return cls.cursor_join(field="domain", condition=condition, query=query)
