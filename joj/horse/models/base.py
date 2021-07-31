from functools import lru_cache
from typing import TYPE_CHECKING, List, Optional, Type, TypeVar

from pydantic import BaseModel
from tortoise import BaseDBAsyncClient, Tortoise, fields, models, queryset

from joj.horse.utils.base import is_uuid

if TYPE_CHECKING:
    from joj.horse.models.domain import Domain
    from joj.horse.schemas.query import OrderingQuery, PaginationQuery


class BaseORMModel(models.Model):
    class Meta:
        abstract = True

    class PydanticMeta:
        backward_relations = False

    id = fields.UUIDField(pk=True)

    created_at = fields.DatetimeField(null=True, auto_now_add=True)
    updated_at = fields.DatetimeField(null=True, auto_now=True)

    def __str__(self) -> str:  # pragma: no cover
        return str({k: v for k, v in self.__dict__.items() if not k.startswith("_")})

    def update_from_schema(self: "BaseORMModel", schema: BaseModel) -> None:
        self.update_from_dict(
            {k: v for k, v in schema.__dict__.items() if v is not None}
        )

    @staticmethod
    def apply_ordering(
        query_set: queryset.QuerySet,
        ordering: Optional["OrderingQuery"],
        prefix: str = "",
    ) -> queryset.QuerySet:
        def add_prefix(x: str) -> str:
            if x.startswith("-"):
                return f"-{prefix}{x[1:]}"
            return f"{prefix}{x}"

        if ordering is not None and ordering.orderings:
            if prefix:
                orderings = [add_prefix(x) for x in ordering.orderings]
            else:
                orderings = ordering.orderings
            query_set = query_set.order_by(*orderings)
        return query_set

    @staticmethod
    def apply_pagination(
        query_set: queryset.QuerySet, pagination: Optional["PaginationQuery"]
    ) -> queryset.QuerySet:
        if pagination is not None:
            query_set = query_set.offset(pagination.offset).limit(pagination.limit)
        return query_set


BaseORMModelType = TypeVar("BaseORMModelType", bound=BaseORMModel)


class URLMixin(BaseORMModel):
    url = fields.CharField(max_length=255, unique=True)

    @classmethod
    async def find_by_url_or_id(
        cls: Type["BaseORMModelType"], url_or_id: str
    ) -> Optional["BaseORMModelType"]:
        if is_uuid(url_or_id):
            return await cls.get_or_none(id=url_or_id)
        else:
            return await cls.get_or_none(url=url_or_id)


class DomainURLMixin(URLMixin):
    if TYPE_CHECKING:
        domain: fields.ForeignKeyRelation["Domain"]

    @classmethod
    async def find_by_domain_url_or_id(
        cls: Type["BaseORMModelType"], domain: "Domain", url_or_id: str
    ) -> Optional["BaseORMModelType"]:
        if is_uuid(url_or_id):
            return await cls.get_or_none(domain=domain, id=url_or_id)
        else:
            return await cls.get_or_none(domain=domain, url=url_or_id)


async def url_pre_save(
    sender: "Type[URLMixin]",
    instance: "URLMixin",
    using_db: "Optional[BaseDBAsyncClient]",
    update_fields: List[str],
) -> None:
    if not instance.url:
        instance.url = str(instance.id)


@lru_cache()
def init_models() -> None:
    Tortoise.init_models(["joj.horse.models"], "models")
