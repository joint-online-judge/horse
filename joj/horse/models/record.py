from pymongo import ASCENDING, DESCENDING, IndexModel
from umongo import fields
from umongo.embedded_document import EmbeddedDocumentImplementation
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument

from joj.horse.models.base import DocumentMixin
from joj.horse.models.domain import Domain
from joj.horse.models.problem import Problem
from joj.horse.models.problem_set import ProblemSet
from joj.horse.models.user import User
from joj.horse.utils.db import instance


@instance.register
class RecordCase(EmbeddedDocumentImplementation):
    status = fields.IntegerField(default=0)
    score = fields.IntegerField(default=0)
    time_ms = fields.IntegerField(default=0)
    memory_kb = fields.IntegerField(default=0)
    execute_status = fields.IntegerField(default=0)
    stdout = fields.StringField(default="")
    stderr = fields.StringField(default="")


@instance.register
class Record(DocumentMixin, MotorAsyncIODocument):
    class Meta:
        collection_name = "records"
        indexes = [
            IndexModel(
                [
                    ("domain", ASCENDING),
                    ("problem", ASCENDING),
                    ("user", ASCENDING),
                    ("submit_at", DESCENDING),
                ]
            ),
            IndexModel(
                [("problem", ASCENDING), ("user", ASCENDING), ("submit_at", DESCENDING)]
            ),
            IndexModel(
                [("domain", ASCENDING), ("user", ASCENDING), ("submit_at", DESCENDING)]
            ),
            IndexModel([("user", ASCENDING), ("submit_at", DESCENDING)]),
        ]

    status = fields.IntegerField(default=0)
    score = fields.IntegerField(default=0)
    time_ms = fields.IntegerField(default=0)
    memory_kb = fields.IntegerField(default=0)
    domain = fields.ReferenceField(Domain)
    problem = fields.ReferenceField(Problem)
    problem_set = fields.ReferenceField(ProblemSet)
    problem_data = fields.IntegerField(default=0)  # modify later
    user = fields.ReferenceField(User)
    code_type = fields.IntegerField()
    code = fields.ObjectIdField()
    judge_category = fields.ListField(fields.StringField())

    submit_at = fields.DateTimeField()
    judge_at = fields.DateTimeField()

    judge_user = fields.ReferenceField(User)

    compiler_texts = fields.StringField(default="")
    cases = fields.ListField(
        fields.EmbeddedField(RecordCase, default=RecordCase()), default=[]
    )
