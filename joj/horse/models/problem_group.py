from joj.horse.models.base import BaseORMModel


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
