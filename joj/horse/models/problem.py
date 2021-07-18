from tortoise import fields

from joj.horse.models.base import BaseORMModel, URLMixin
from joj.horse.models.domain import Domain
from joj.horse.models.problem_group import ProblemGroup
from joj.horse.models.user import User


class Problem(URLMixin, BaseORMModel):
    class Meta:
        table = "problems"

    domain: fields.ForeignKeyRelation[Domain] = fields.ForeignKeyField(
        "models.Domain",
        related_name="problems",
        on_delete=fields.CASCADE,
        index=True,
    )
    owner: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User",
        related_name="owned_problems",
        on_delete=fields.RESTRICT,
        index=True,
    )
    problem_group: fields.ForeignKeyRelation[ProblemGroup] = fields.ForeignKeyField(
        "models.ProblemGroup",
        related_name="problems",
        on_delete=fields.SET_NULL,
        null=True,
        index=True,
    )

    title = fields.CharField(max_length=255)
    content = fields.CharField(max_length=255, default="")
    hidden = fields.BooleanField(default=False)
    num_submit = fields.IntField(default=0)
    num_accept = fields.IntField(default=0)

    data_version = fields.IntField(default=2)
    languages = fields.TextField(default="[]")


# @instance.register
# class Problem(DocumentMixin, MotorAsyncIODocument):
#     class Meta:
#         collection_name = "problems"
#         indexes = [
#             IndexModel("domain"),
#             IndexModel("owner"),
#             IndexModel("problem_group"),
#             IndexModel("problem_set"),
#         ]
#         strict = False
#
#     domain = fields.ReferenceField(Domain, required=True)
#     owner = fields.ReferenceField(User, required=True)
#     problem_group = fields.ReferenceField(ProblemGroup, required=True)
#     # problem_set = fields.ReferenceField(ProblemSet, required=True)
#
#     url = fields.StringField(required=True)
#     title = fields.StringField(required=True)
#     content = fields.StringField(default="")
#     hidden = fields.BooleanField(default=False)
#     num_submit = fields.IntegerField(default=0)
#     num_accept = fields.IntegerField(default=0)
#
#     data = fields.IntegerField()  # modify later
#     data_version = fields.IntegerField(default=2)
#     languages = fields.ListField(fields.StringField(), default=List(str))
