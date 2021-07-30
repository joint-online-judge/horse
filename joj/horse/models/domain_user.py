from typing import Union

from tortoise import fields

from joj.horse.models.base import BaseORMModel
from joj.horse.models.domain import Domain
from joj.horse.models.domain_role import DomainRole
from joj.horse.models.permission import DefaultRole
from joj.horse.models.user import User
from joj.horse.utils.errors import BizError, ErrorCode


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

    @classmethod
    async def add_domain_user(
        cls, domain: Domain, user: User, role: Union[str, DefaultRole]
    ) -> "DomainUser":
        role = str(role)
        # check domain user
        if await DomainUser.get_or_none(domain=domain, user=user):
            raise BizError(ErrorCode.UserAlreadyInDomainBadRequestError)
        # check domain role
        await DomainRole.ensure_exists(domain=domain, role=role)
        # add member
        domain_user = await DomainUser.create(domain=domain, user=user, role=role)
        return domain_user


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
