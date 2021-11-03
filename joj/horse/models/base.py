from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, TypeVar, Union
from uuid import UUID, uuid4

from pydantic.datetime_parse import parse_datetime
from sqlalchemy.engine import Connection
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Mapper
from sqlalchemy.sql.expression import Delete, Select, Update
from sqlalchemy.sql.functions import FunctionElement
from sqlalchemy.sql.schema import Column
from sqlalchemy.types import DateTime
from sqlmodel import Field, SQLModel, delete, select, update

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


@compiles(utcnow, "mssql")
def ms_utcnow(element: Any, compiler: Any, **kwargs: Any) -> str:
    return "GETUTCDATE()"


def get_datetime_column(**kwargs: Any) -> Column:
    if "index" not in kwargs:
        kwargs["index"] = True
    if "nullable" not in kwargs:
        kwargs["nullable"] = False
    return Column(DateTime(timezone=True), **kwargs)


class UTCDatetime(datetime):
    """parse a datetime and convert in into UTC format"""

    @classmethod
    def __get_validators__(cls) -> Any:
        yield cls.validate

    @classmethod
    def validate(cls, v: Any) -> datetime:
        return datetime.fromtimestamp(parse_datetime(v).timestamp())


class BaseORMModel(SQLModel):
    id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False)
    created_at: Optional[datetime] = Field(
        None, sa_column=get_datetime_column(server_default=utcnow())
    )
    updated_at: Optional[datetime] = Field(
        None, sa_column=get_datetime_column(server_default=utcnow(), onupdate=utcnow())
    )

    def update_from_dict(self: "BaseORMModel", d: Dict[str, Any]) -> None:
        for k, v in d.items():
            if v is not None:
                setattr(self, k, v)

    @classmethod
    def sql_select(cls) -> Select:
        return select(cls)

    @classmethod
    def sql_update(cls) -> Update:
        return update(cls)

    @classmethod
    def sql_delete(cls) -> Delete:
        return delete(cls)

    @classmethod
    async def get_or_none(
        __base_orm_model_cls__: Type["BaseORMModelType"], **kwargs: Any
    ) -> Optional["BaseORMModelType"]:
        async with db_session() as session:
            statement = __base_orm_model_cls__.apply_filtering(
                select(__base_orm_model_cls__), **kwargs
            )
            results = await session.exec(statement)
            return results.one_or_none()

    @classmethod
    async def get_many(
        __base_orm_model_cls__: Type["BaseORMModelType"], **kwargs: Any
    ) -> List["BaseORMModelType"]:
        async with db_session() as session:
            statement = __base_orm_model_cls__.apply_filtering(
                select(__base_orm_model_cls__), **kwargs
            )
            results = await session.exec(statement)
            return results.all()

    async def save_model(self, commit: bool = True, refresh: bool = True) -> None:
        async with db_session() as session:
            session.sync_session.add(self)
            if commit:
                await session.commit()
            if refresh:
                await session.refresh(self)

    async def delete_model(self, commit: bool = True) -> None:
        async with db_session() as session:
            session.sync_session.delete(self)
            if commit:
                await session.commit()

    @classmethod
    def apply_ordering(
        __base_orm_model_cls__: Type["BaseORMModelType"],
        statement: Select,
        ordering: Optional["OrderingQuery"],
        prefix: str = "",
    ) -> Select:
        # def add_prefix(x: str) -> str:
        #     if x.startswith("-"):
        #         return f"-{prefix}{x[1:]}"
        #     return f"{prefix}{x}"

        if ordering is not None and ordering.orderings:
            for x in ordering.orderings:
                if x.startswith("-"):
                    # TODO: write this
                    pass
            # if prefix:
            #     orderings = [add_prefix(x) for x in ordering.orderings]
            # else:
            #     orderings = ordering.orderings
            # statement.order_by()
            # query_set = query_set.order_by(*orderings)
        return statement

    @staticmethod
    def apply_pagination(
        statement: Select,
        pagination: Optional["PaginationQuery"],
    ) -> Select:
        if pagination is not None:
            statement = statement.offset(pagination.offset).limit(pagination.limit)
        return statement

    @classmethod
    def apply_filtering(
        __base_orm_model_cls__: Type["BaseORMModelType"],
        __statement__: Union[Select, Update, Delete],
        **kwargs: Any,
    ) -> Union[Select, Update, Delete]:
        statement = select(__base_orm_model_cls__)
        for k, v in kwargs.items():
            statement = statement.where(getattr(__base_orm_model_cls__, k) == v)
        return statement


BaseORMModelType = TypeVar("BaseORMModelType", bound=BaseORMModel)


class URLMixin(SQLModel):
    url: UserInputURL = Field("", description="(unique) url of the domain")


class URLORMModel(URLMixin, BaseORMModel):
    url: str = Field(..., sa_column_kwargs={"unique": True})

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


class DomainURLORMModel(URLORMModel):
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


def url_pre_save(mapper: Mapper, connection: Connection, target: URLORMModel) -> None:
    if not target.url:
        target.url = str(target.id)
