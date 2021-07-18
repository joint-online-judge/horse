from pymongo import ASCENDING, IndexModel
from tortoise import BaseDBAsyncClient, fields, models, signals
from umongo import fields
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument

from joj.horse.models.base import BaseORMModel, DocumentMixin, URLMixin
from joj.horse.models.domain import Domain
from joj.horse.models.problem import Problem
from joj.horse.models.user import User
from joj.horse.utils.db import instance


class ProblemSet(URLMixin, BaseORMModel):
    class Meta:
        table = "problem_sets"

    domain: fields.ForeignKeyRelation[Domain] = fields.ForeignKeyField(
        "models.Domain",
        related_name="problem_sets",
        on_delete=fields.CASCADE,
        index=True,
    )
    owner: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User",
        related_name="owned_problem_sets",
        on_delete=fields.RESTRICT,
        index=True,
    )
    title = fields.CharField(max_length=255)
    content = fields.CharField(max_length=255, default="")
    hidden = fields.BooleanField(default=False)
    scoreboard_hidden = fields.BooleanField(default=False)

    available_time = fields.DatetimeField()
    due_time = fields.DatetimeField()
    num_submit = fields.IntField(default=0)
    num_accept = fields.IntField(default=0)

    problems: fields.ManyToManyRelation[Problem] = fields.ManyToManyField(
        "models.Problem",
        through="problem_set_problems",
        related_name="problem_sets",
        on_delete=fields.CASCADE,
    )


# @instance.register
# class ProblemSet(DocumentMixin, MotorAsyncIODocument):
#     class Meta:
#         collection_name = "problem.sets"
#         indexes = [
#             IndexModel("domain"),
#             IndexModel("owner"),
#             IndexModel([("domain", ASCENDING), ("url", ASCENDING)], unique=True),
#         ]
#         strict = False
#
#     domain = fields.ReferenceField(Domain, required=True)
#     owner = fields.ReferenceField(User, required=True)
#
#     url = fields.StringField(required=True)
#     title = fields.StringField(required=True)
#     content = fields.StringField(default="")
#     hidden = fields.BooleanField(default=False)
#     scoreboard_hidden = fields.BooleanField(default=False)
#     available_time = fields.DateTimeField()
#     due_time = fields.DateTimeField()
#     num_submit = fields.IntegerField(default=0)
#     num_accept = fields.IntegerField(default=0)
#
#     problems = fields.ListField(fields.ReferenceField(Problem), default=[])
