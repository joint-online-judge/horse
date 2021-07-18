from tortoise import fields

from joj.horse.models.base import BaseORMModel
from joj.horse.models.domain import Domain
from joj.horse.models.user import User


class DomainUser(BaseORMModel):
    class Meta:
        table = "domain_users"
        unique_together = [
            ("domain", "user"),
        ]

    domain: fields.ForeignKeyRelation[Domain] = fields.ForeignKeyField(
        "models.Domain",
        related_name="users",
        on_delete=fields.CASCADE,
        index=True,
    )
    user: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User",
        related_name="domains",
        on_delete=fields.CASCADE,
        index=True,
    )
    role = fields.CharField(max_length=255)


# @instance.register
# class DomainUser(DocumentMixin, MotorAsyncIODocument):
#     class Meta:
#         collection_name = "domain.users"
#         indexes = [
#             IndexModel("domain"),
#             IndexModel("user"),
#             IndexModel([("domain", ASCENDING), ("user", ASCENDING)], unique=True),
#         ]
#         strict = False
#
#     domain = fields.ReferenceField(Domain, required=True)
#     user = fields.ReferenceField(User, required=True)
#     role = fields.StringField(required=True)
#
#     join_at = fields.DateTimeField(required=True)
#
#     @classmethod
#     def cursor_find_user_domains(
#         cls, user: User, role: Optional[List[str]], query: Optional[BaseQuery] = None
#     ) -> AsyncIOMotorCursor:
#         condition = {}
#         if user.role != "root":
#             condition["user"] = user.id
#         if role is not None:
#             condition["role"] = {"$in": role}
#         return cls.cursor_join(field="domain", condition=condition, query=query)
#
#     @classmethod
#     async def add_domain_user(
#         cls, domain: ObjectId, user: ObjectId, role: str
#     ) -> "DomainUser":
#         # check domain user
#         if await DomainUser.find_one({"domain": domain, "user": user}):
#             raise BizError(ErrorCode.UserAlreadyInDomainBadRequestError)
#         # check domain role
#         await DomainRole.ensure_exists(domain=domain, role=role)
#         # add member
#         domain_user_schema = DomainUserSchema(domain=domain, user=user, role=role)
#         domain_user_model = DomainUser(**domain_user_schema.to_model())
#         await domain_user_model.commit()
#         return domain_user_model
#
#     @classmethod
#     async def update_domain_user(
#         cls, domain: ObjectId, user: ObjectId, role: str
#     ) -> "DomainUser":
#         # check domain user
#         domain_user_model = await DomainUser.find_one({"domain": domain, "user": user})
#         if domain_user_model is None:
#             raise BizError(ErrorCode.UserAlreadyInDomainBadRequestError)
#         # check domain role
#         await DomainRole.ensure_exists(domain=domain, role=role)
#         # update role
#         domain_user_model.role = role
#         await domain_user_model.commit()
#         return domain_user_model
