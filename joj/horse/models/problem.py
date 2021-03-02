from pymongo import IndexModel
from umongo import fields
from umongo.data_objects import List
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument

from joj.horse.models.base import DocumentMixin
from joj.horse.models.domain import Domain
from joj.horse.models.problem_group import ProblemGroup
from joj.horse.models.user import User
from joj.horse.utils.db import instance


@instance.register
class Problem(DocumentMixin, MotorAsyncIODocument):
    class Meta:
        collection_name = "problems"
        indexes = [
            IndexModel("domain"),
            IndexModel("owner"),
            IndexModel("group", sparse=True),
        ]

    domain = fields.ReferenceField(Domain, required=True)
    owner = fields.ReferenceField(User, required=True)
    group = fields.ReferenceField(ProblemGroup, required=True)

    title = fields.StringField(required=True)
    content = fields.StringField(default="")
    hidden = fields.BooleanField(default=False)
    num_submit = fields.IntegerField(default=0)
    num_accept = fields.IntegerField(default=0)

    data = fields.IntegerField()  # modify later
    data_version = fields.IntegerField(default=2)
    languages = fields.ListField(fields.StringField(), default=List(str))
