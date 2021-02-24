from pymongo import IndexModel
from umongo import fields
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument

from joj.horse.models.base import DocumentMixin
from joj.horse.models.domain import Domain
from joj.horse.models.problem import Problem
from joj.horse.models.user import User
from joj.horse.utils.db import instance


@instance.register
class ProblemSet(MotorAsyncIODocument, DocumentMixin):
    class Meta:
        collection_name = "problem.sets"
        indexes = [
            IndexModel("domain"), # TODO: is it appropriate?
        ]

    domain = fields.ReferenceField(Domain, required=True)
    owner = fields.ReferenceField(User, required=True)

    title = fields.StringField(required=True)
    content = fields.StringField(default="")
    hidden = fields.BooleanField(default=False)
    num_submit = fields.IntegerField(default=0)
    num_accept = fields.IntegerField(default=0)

    problems = fields.ListField(
        fields.ReferenceField(Problem, required=True), default=[]
    )
