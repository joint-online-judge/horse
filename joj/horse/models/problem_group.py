from umongo import fields
from umongo.data_objects import List
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument

from joj.horse.models.base import DocumentMixin
from joj.horse.utils.db import instance


@instance.register
class ProblemGroup(DocumentMixin, MotorAsyncIODocument):
    class Meta:
        collection_name = "problem.groups"
        strict = False

    moss_results = fields.ListField(fields.StringField(), default=[])
