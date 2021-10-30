from datetime import datetime
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, TypeVar
from uuid import UUID, uuid4

from pydantic import BaseModel, root_validator
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import FunctionElement
from sqlalchemy.types import DateTime
from sqlmodel import Field, SQLModel, select
from tortoise import BaseDBAsyncClient, Tortoise, queryset

from joj.horse.schemas.base import UserInputURL
from joj.horse.utils.base import is_uuid
from joj.horse.utils.db import db_session

if TYPE_CHECKING:
    from joj.horse.models.domain import Domain
    from joj.horse.schemas.query import OrderingQuery, PaginationQuery


class utcnow(FunctionElement):
    type = DateTime()


@compiles(utcnow, "postgresql")
def pg_utcnow(element: Any, compiler: Any, **kwargs: Any) -> str:
    return "TIMEZONE('utc', CURRENT_TIMESTAMP)"


class BaseORMModel(SQLModel):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    created_at: Optional[datetime] = Field(
        None, sa_column_kwargs={"server_default": utcnow()}
    )
    updated_at: Optional[datetime] = Field(
        None, sa_column_kwargs={"server_default": utcnow(), "onupdate": utcnow()}
    )

    # def __str__(self) -> str:
    #     return str({k: v for k, v in self.__dict__.items() if not k.startswith("_")})
    #
    def update_from_schema(self: "BaseORMModel", schema: BaseModel) -> None:
        for k, v in schema.dict().items():
            if v is not None:
                setattr(self, k, v)
        # self.update_from_dict(
        #     {k: v for k, v in schema.dict().items() if v is not None}
        # )

    @classmethod
    async def get_or_none(
        __base_orm_model_cls__: Type["BaseORMModelType"], **kwargs: Any
    ) -> Optional["BaseORMModelType"]:
        async with db_session() as session:
            statement = select(__base_orm_model_cls__)
            for k, v in kwargs.items():
                statement = statement.where(getattr(__base_orm_model_cls__, k) == v)
            results = await session.exec(statement)
            return results.one_or_none()

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


class URLMixin(SQLModel):
    url: UserInputURL = Field("", description="(unique) url of the domain")


class URLORMModel(URLMixin, BaseORMModel):
    url: str = Field(..., sa_column_kwargs={"unique": True})

    @root_validator()
    def validate_url(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if "url" not in values or not values["url"]:
            values["url"] = str(values["id"])
        return values

    @classmethod
    async def find_by_url_or_id(
        cls: Type["BaseORMModelType"], url_or_id: str
    ) -> Optional["BaseORMModelType"]:
        if is_uuid(url_or_id):
            statement = select(cls).where(cls.id == url_or_id)
        else:
            statement = select(cls).where(cls.url == url_or_id)
        async with db_session() as session:
            result = await session.exec(statement)
            return result.one_or_none()


class DomainURLMixin(URLMixin):
    if TYPE_CHECKING:
        domain_id: UUID

    @classmethod
    async def find_by_domain_url_or_id(
        cls: Type["BaseORMModelType"], domain: "Domain", url_or_id: str
    ) -> Optional["BaseORMModelType"]:
        if is_uuid(url_or_id):
            statement = (
                select(cls).where(cls.id == url_or_id).where(cls.domain_id == domain.id)
            )
        else:
            statement = (
                select(cls)
                .where(cls.url == url_or_id)
                .where(cls.domain_id == domain.id)
            )
        async with db_session() as session:
            result = await session.exec(statement)
            return result.one_or_none()


async def url_pre_save(
    sender: "Type[URLMixin]",
    instance: "URLMixin",
    using_db: "Optional[BaseDBAsyncClient]",
    update_fields: List[str],
) -> None:
    if not instance.id:
        instance.id = uuid4()
    if not instance.url:
        instance.url = str(instance.id)


@lru_cache()
def init_models() -> None:
    Tortoise.init_models(["joj.horse.models"], "models")
