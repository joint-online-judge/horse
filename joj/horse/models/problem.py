from typing import TYPE_CHECKING, List, Optional, Tuple
from uuid import UUID

from tortoise import fields, signals

from joj.horse.models.base import BaseORMModel, DomainURLMixin, url_pre_save
from joj.horse.models.domain import Domain
from joj.horse.models.problem_group import ProblemGroup
from joj.horse.models.user import User

if TYPE_CHECKING:
    from joj.horse.models.problem_set import ProblemSet
    from joj.horse.schemas.query import OrderingQuery, PaginationQuery


class Problem(DomainURLMixin, BaseORMModel):
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
        on_delete=fields.RESTRICT,
        index=True,
    )

    title = fields.CharField(max_length=255)
    content = fields.CharField(max_length=255, default="")
    hidden = fields.BooleanField(default=False)
    num_submit = fields.IntField(default=0)
    num_accept = fields.IntField(default=0)

    data_version = fields.IntField(default=2)
    languages = fields.JSONField(default="[]")

    if TYPE_CHECKING:
        problem_group_id: UUID

    @classmethod
    async def find_by_domain(
        cls,
        domain: Domain,
        include_hidden: bool = False,
        problem_set: Optional["ProblemSet"] = None,
        problem_group: Optional["ProblemGroup"] = None,
        ordering: Optional["OrderingQuery"] = None,
        pagination: Optional["PaginationQuery"] = None,
    ) -> Tuple[List["Problem"], int]:
        if problem_set:
            query_set = problem_set.problems.filter(domain=domain)
        else:
            query_set = domain.problems.all()
        if not include_hidden:
            query_set = query_set.filter(hidden=False)
        if problem_group:
            query_set = query_set.filter(problem_group=problem_group)
        query_set = cls.apply_ordering(query_set, ordering)
        count = await query_set.count()
        query_set = cls.apply_pagination(query_set, pagination)
        return await query_set, count


signals.pre_save(Problem)(url_pre_save)


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
