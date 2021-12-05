from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, TypeVar, Union
from uuid import UUID, uuid4

from pydantic.fields import Undefined
from sqlalchemy.engine import Connection, Row
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import Mapper
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql.expression import Delete, Select, Update
from sqlalchemy.sql.functions import count
from sqlmodel import Field, SQLModel, delete, select, update
from sqlmodel.engine.result import ScalarResult

from joj.horse.schemas.base import BaseModel, UserInputURL, get_datetime_column, utcnow
from joj.horse.utils.base import is_uuid
from joj.horse.utils.db import db_session

if TYPE_CHECKING:
    from joj.horse.models.domain import Domain
    from joj.horse.schemas.query import OrderingQuery, PaginationQuery


class ORMUtils(SQLModel, BaseModel):
    def update_from_dict(self: "BaseORMModel", d: Dict[str, Any]) -> None:
        for k, v in d.items():
            if v is not Undefined:
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
    async def session_exec(cls, statement: Select) -> ScalarResult["BaseORMModelType"]:
        async with db_session() as session:
            return await session.exec(statement)

    @classmethod
    async def get_or_none(
        __base_orm_model_cls__: Type["BaseORMModelType"], **kwargs: Any
    ) -> Optional["BaseORMModelType"]:
        async with db_session() as session:
            statement = __base_orm_model_cls__.apply_filtering(
                select(__base_orm_model_cls__), **kwargs
            )
            try:
                results = await session.exec(statement)
            except StatementError:
                return None
            return results.one_or_none()

    @classmethod
    async def get_many(
        __base_orm_model_cls__: Type["BaseORMModelType"], **kwargs: Any
    ) -> List["BaseORMModelType"]:
        async with db_session() as session:
            statement = __base_orm_model_cls__.apply_filtering(
                select(__base_orm_model_cls__), **kwargs
            )
            try:
                results = await session.exec(statement)
            except StatementError:
                return []
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

    async def refresh_model(self) -> None:
        async with db_session() as session:
            await session.refresh(self)

    async def fetch_related(self, *fields: str) -> None:
        def sync_func(_: Any) -> None:
            for field in fields:
                getattr(self, field)

        async with db_session() as session:
            await session.run_sync(sync_func)

    @classmethod
    def apply_ordering(
        cls: Type["BaseORMModelType"],
        statement: Select,
        ordering: Optional["OrderingQuery"],
    ) -> Select:
        if ordering is None or not ordering.orderings:
            return statement
        order_by_clause = []
        for x in ordering.orderings:
            asc: Optional[bool] = None
            if x.startswith("-"):
                asc = False
                field = x[1:]
            elif x.startswith("+"):
                asc = True
                field = x[1:]
            else:
                asc = None
                field = x
            if field.startswith("_"):
                continue
            sa_column = getattr(cls, field, None)
            if sa_column is not None and isinstance(sa_column, InstrumentedAttribute):
                if asc is None:
                    order_by_clause.append(sa_column)
                elif asc:
                    order_by_clause.append(sa_column.asc())
                else:
                    order_by_clause.append(sa_column.desc())
        if len(order_by_clause) > 0:
            statement = statement.order_by(*order_by_clause)
        return statement

    @classmethod
    def apply_count(
        cls: Type["BaseORMModelType"],
        statement: Select,
        # alt_cls: Optional[Type["BaseORMModelType"]] = None,
    ) -> Select:
        # if alt_cls is None:
        #     alt_cls = cls
        return statement.with_only_columns(count(), maintain_column_froms=True)

    @classmethod
    def apply_pagination(
        cls: Type["BaseORMModelType"],
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

    @classmethod
    async def execute_list_statement(
        cls: Type["BaseORMModelType"],
        statement: Select,
        ordering: Optional["OrderingQuery"] = None,
        pagination: Optional["PaginationQuery"] = None,
    ) -> Tuple[Union[List["BaseORMModelType"], List[Row]], int]:
        count_statement = cls.apply_count(statement)
        statement = cls.apply_ordering(statement, ordering)
        statement = cls.apply_pagination(statement, pagination)

        async with db_session() as session:
            try:
                row_count = await session.exec(count_statement)
                results = await session.exec(statement)
            except StatementError:
                return [], 0
            row_count_value = row_count.one()
            if not isinstance(row_count_value, int):
                row_count_value = row_count_value[0]
            return results.all(), row_count_value

    @staticmethod
    def parse_rows(
        rows: List[Row], *tables: Type["BaseORMModelType"]
    ) -> Tuple[List["BaseORMModelType"], ...]:
        if len(rows) == 0:
            return tuple([] for _ in tables)
        return tuple(list(x) for x in zip(*rows))


class BaseORMModel(ORMUtils):
    id: UUID = Field(default_factory=uuid4, primary_key=True, nullable=False)
    created_at: Optional[datetime] = Field(
        None, sa_column=get_datetime_column(server_default=utcnow())
    )
    updated_at: Optional[datetime] = Field(
        None, sa_column=get_datetime_column(server_default=utcnow(), onupdate=utcnow())
    )


BaseORMModelType = TypeVar("BaseORMModelType", bound=ORMUtils)


class URLMixin(BaseORMModel):
    url: UserInputURL = Field("", description="(unique) url of the domain")


class URLORMModel(BaseORMModel):
    url: str = Field(..., index=True, nullable=False, sa_column_kwargs={"unique": True})

    @classmethod
    async def find_by_url_or_id(
        cls: Type["BaseORMModelType"], url_or_id: str
    ) -> Optional["BaseORMModelType"]:
        if is_uuid(url_or_id):
            statement = select(cls).where(cls.id == url_or_id)
        else:
            statement = select(cls).where(cls.url == url_or_id)
        async with db_session() as session:
            try:
                result = await session.exec(statement)
            except StatementError:
                return None
            return result.one_or_none()


class DomainURLORMModel(URLORMModel):
    if TYPE_CHECKING:
        domain_id: UUID

    url: str = Field(..., index=True, nullable=False)

    @classmethod
    async def find_by_domain_url_or_id(
        cls: Type["BaseORMModelType"],
        domain: "Domain",
        url_or_id: str,
        options: Any = None,
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
        if options:
            if isinstance(options, list):
                statement = statement.options(*options)
            else:
                statement = statement.options(options)
        async with db_session() as session:
            try:
                result = await session.exec(statement)
            except StatementError:
                return None
            return result.one_or_none()


def url_pre_save(mapper: Mapper, connection: Connection, target: URLORMModel) -> None:
    if not target.url:
        target.url = str(target.id)
