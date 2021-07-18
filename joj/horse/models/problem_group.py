from tortoise import BaseDBAsyncClient, fields, models, signals
from umongo import fields
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument

from joj.horse.models.base import BaseORMModel, DocumentMixin
from joj.horse.models.domain import Domain
from joj.horse.utils.db import instance


class ProblemGroup(BaseORMModel):
    class Meta:
        table = "problem_groups"


# @instance.register
# class ProblemGroup(DocumentMixin, MotorAsyncIODocument):
#     class Meta:
#         collection_name = "problem.groups"
#         strict = False
#
#     moss_results = fields.ListField(fields.StringField(), default=[])
