import typing

from pymongo import IndexModel
from umongo import fields
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument

if typing.TYPE_CHECKING:
    from joj.horse.models.problem import Problem

from joj.horse.models.base import DocumentMixin
from joj.horse.utils.db import instance


@instance.register
class ProblemGroup(DocumentMixin, MotorAsyncIODocument):
    class Meta:
        collection_name = "problem.groups"
        indexes = [IndexModel("problems")]  # TODO: appropriate indexes

    problems = fields.ListField(
        fields.ReferenceField("Problem", required=True), default=[]
    )
