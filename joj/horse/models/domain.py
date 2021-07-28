from typing import TYPE_CHECKING, List, Optional, Tuple
from uuid import UUID

from tortoise import fields, queryset, signals

from joj.horse.models.base import BaseORMModel, URLMixin, url_pre_save
from joj.horse.models.user import User

if TYPE_CHECKING:
    from joj.horse.models import (
        DomainRole,
        DomainUser,
        Problem,
        ProblemGroup,
        ProblemSet,
    )
    from joj.horse.schemas.query import OrderingQuery, PaginationQuery


class Domain(URLMixin, BaseORMModel):
    class Meta:
        table = "domains"

    name = fields.CharField(max_length=255, index=True)
    owner: fields.ForeignKeyRelation[User] = fields.ForeignKeyField(
        "models.User",
        related_name="owned_domains",
        on_delete=fields.RESTRICT,
        index=True,
    )

    gravatar = fields.CharField(max_length=255, default="")
    bulletin = fields.TextField(default="")

    if TYPE_CHECKING:
        owner_id: UUID
        roles: queryset.QuerySet[DomainRole]
        users: queryset.QuerySet[DomainUser]
        problems: queryset.QuerySet[Problem]

    async def find_problems(
        self,
        include_hidden: bool = False,
        problem_set: Optional["ProblemSet"] = None,
        problem_group: Optional["ProblemGroup"] = None,
        ordering: Optional["OrderingQuery"] = None,
        pagination: Optional["PaginationQuery"] = None,
    ) -> Tuple[List["Problem"], int]:
        if problem_set:
            query_set = problem_set.problems.filter(domain=self)
        else:
            query_set = self.problems.all()
        if not include_hidden:
            query_set = query_set.filter(hidden=False)
        if problem_group:
            query_set = query_set.filter(problem_group=problem_group)
        query_set = self.apply_ordering(query_set, ordering)
        count = await query_set.count()
        query_set = self.apply_pagination(query_set, pagination)
        problems = await query_set
        return problems, count


signals.pre_save(Domain)(url_pre_save)

# @instance.register
# class Domain(DocumentMixin, MotorAsyncIODocument):
#     class Meta:
#         collection_name = "domains"
#         indexes = [
#             IndexModel("url", unique=True),
#             IndexModel("owner"),
#             IndexModel("name"),
#         ]
#         strict = False
#
#     url = fields.StringField(required=True)
#     name = fields.StringField(required=True)
#     owner = fields.ReferenceField(User, required=True)
#
#     gravatar = fields.StringField(default="")
#     bulletin = fields.StringField(default="")
#
#     # invitation_code = fields.StringField(default="")
#     # invitation_expire_at = fields.DateTimeField(default=datetime(1970, 1, 1))
#
#     @classmethod
#     async def find_by_url_or_id(cls: MotorAsyncIODocument, url_or_id: str) -> Any:
#         if ObjectId.is_valid(url_or_id):
#             filter = {"_id": ObjectId(url_or_id)}
#         else:
#             filter = {"url": url_or_id}
#         return await cls.find_one(filter)
