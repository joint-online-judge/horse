from tortoise import fields

from joj.horse.models.base import BaseORMModel
from joj.horse.models.domain import Domain
from joj.horse.utils.errors import BizError, ErrorCode


class DomainRole(BaseORMModel):
    class Meta:
        table = "domain_roles"
        unique_together = [
            ("domain", "role"),
        ]

    domain: fields.ForeignKeyRelation[Domain] = fields.ForeignKeyField(
        "models.Domain",
        related_name="roles",
        on_delete=fields.CASCADE,
        index=True,
    )
    role = fields.CharField(max_length=255)
    permission = fields.JSONField()

    @classmethod
    async def ensure_exists(cls, domain: Domain, role: str) -> None:
        if await DomainRole.get_or_none(domain=domain, role=role) is None:
            raise BizError(ErrorCode.DomainRoleNotFoundError)


# @instance.register
# class DomainRole(DocumentMixin, MotorAsyncIODocument):
#     class Meta:
#         collection_name = "domain.roles"
#         indexes = [
#             IndexModel("domain"),
#             IndexModel("role"),
#             IndexModel([("domain", ASCENDING), ("role", ASCENDING)], unique=True),
#         ]
#         strict = False
#
#     domain = fields.ReferenceField(Domain, required=True)
#     role = fields.StringField(required=True)
#     permission = fields.EmbeddedField(DomainPermission, default=DomainPermission())
#
#     updated_at = fields.DateTimeField(required=True)
#
