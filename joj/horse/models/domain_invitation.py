from tortoise import fields

from joj.horse.models.base import BaseORMModel
from joj.horse.models.domain import Domain


class DomainInvitation(BaseORMModel):
    class Meta:
        table = "domain_invitations"
        unique_together = [
            ("domain", "code"),
        ]

    domain: fields.ForeignKeyRelation[Domain] = fields.ForeignKeyField(
        "models.Domain",
        related_name="invitations",
        on_delete=fields.CASCADE,
        index=True,
    )
    code = fields.CharField(max_length=255, index=True)
    role = fields.CharField(max_length=255)

    expire_at = fields.DatetimeField()


# @instance.register
# class DomainInvitation(DocumentMixin, MotorAsyncIODocument):
#     class Meta:
#         collection_name = "domain.invitations"
#         indexes = [
#             IndexModel("domain"),
#             IndexModel("code"),
#             IndexModel([("domain", ASCENDING), ("code", ASCENDING)], unique=True),
#         ]
#         strict = False
#
#     domain = fields.ReferenceField(Domain, required=True)
#     code = fields.StringField(required=True)
#     role = fields.StringField(required=True)
#
#     expire_at = fields.DateTimeField(required=False)
