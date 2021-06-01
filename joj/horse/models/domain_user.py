from typing import List, Optional

from bson import ObjectId
from pymongo import ASCENDING, IndexModel
from umongo import fields
from umongo.frameworks.motor_asyncio import AsyncIOMotorCursor, MotorAsyncIODocument

from joj.horse.models.base import DocumentMixin
from joj.horse.models.domain import Domain
from joj.horse.models.domain_role import DomainRole
from joj.horse.models.user import User
from joj.horse.schemas.domain_user import DomainUser as DomainUserSchema
from joj.horse.schemas.query import BaseQuery
from joj.horse.utils.db import instance
from joj.horse.utils.errors import BizError, ErrorCode


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
        cls,
        user_id: ObjectId,
        role: Optional[List[str]],
        query: Optional[BaseQuery] = None,
    ) -> AsyncIOMotorCursor:
        condition = {"user": user_id}
        if role is not None:
            condition["role"] = {"$in": role}
        return cls.cursor_join(field="domain", condition=condition, query=query)

    @classmethod
    async def add_domain_user(
        cls, domain: ObjectId, user: ObjectId, role: str
    ) -> "DomainUser":
        # check domain user
        if await DomainUser.find_one({"domain": domain, "user": user}):
            raise BizError(ErrorCode.UserAlreadyInDomainBadRequestError)
        # check domain role
        await DomainRole.ensure_exists(domain=domain, role=role)
        # add member
        domain_user_schema = DomainUserSchema(domain=domain, user=user, role=role)
        domain_user_model = DomainUser(**domain_user_schema.to_model())
        await domain_user_model.commit()
        return domain_user_model

    @classmethod
    async def update_domain_user(
        cls, domain: ObjectId, user: ObjectId, role: str
    ) -> "DomainUser":
        # check domain user
        domain_user_model = await DomainUser.find_one({"domain": domain, "user": user})
        if domain_user_model is None:
            raise BizError(ErrorCode.UserAlreadyInDomainBadRequestError)
        # check domain role
        await DomainRole.ensure_exists(domain=domain, role=role)
        # update role
        domain_user_model.role = role
        await domain_user_model.commit()
        return domain_user_model
