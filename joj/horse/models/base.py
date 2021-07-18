import uuid
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, TypeVar

from bson import ObjectId
from pydantic import BaseModel
from tortoise import BaseDBAsyncClient, Tortoise, fields, models
from umongo import data_objects
from umongo.frameworks.motor_asyncio import AsyncIOMotorCursor, MotorAsyncIODocument

from joj.horse.utils.base import is_uuid
from joj.horse.utils.errors import UnprocessableEntityError

if TYPE_CHECKING:
    from joj.horse.schemas.query import BaseQuery


class DocumentMixin:
    __slots__ = ()

    @classmethod
    async def find_by_id(cls: MotorAsyncIODocument, _id: str) -> Any:
        if not ObjectId.is_valid(_id):
            raise UnprocessableEntityError("Invalid ObjectId")
        return await cls.find_one({"_id": ObjectId(_id)})

    @classmethod
    def aggregate(
        cls: MotorAsyncIODocument, pipeline: Any, **kwargs: Any
    ) -> AsyncIOMotorCursor:
        return cls.collection.aggregate(pipeline, **kwargs)

    @classmethod
    def update_many(
        cls: MotorAsyncIODocument,
        condition: Dict[str, Any],
        update: Dict[str, Any],
        **kwargs: Any
    ) -> AsyncIOMotorCursor:
        return cls.collection.update_many(condition, update, **kwargs)

    def unfetch_all(self: MotorAsyncIODocument) -> None:
        for field in self._data.values():
            if isinstance(field, data_objects.Reference):
                field._document = None
            if isinstance(field, data_objects.List):
                for item in field:
                    if isinstance(item, data_objects.Reference):
                        item._document = None
            if isinstance(field, data_objects.Dict):
                for key, value in field:
                    if isinstance(key, data_objects.Reference):
                        key._document = None
                    if isinstance(value, data_objects.Reference):
                        value._document = None

    def update_from_schema(self: MotorAsyncIODocument, schema: BaseModel) -> None:
        self.update({k: v for k, v in schema.__dict__.items() if v is not None})

    async def set_url_from_id(self: MotorAsyncIODocument) -> bool:
        """
        Update url by _id if it is not a uuid
        """
        if "url" not in self._data.keys():
            return False
        try:
            uuid.UUID(str(self._data.get("url")))
        except ValueError:
            return False
        self.update({"url": str(self.id)})
        await self.commit()
        return True

    @staticmethod
    def generate_join_pipeline(
        field: str,
        condition: Dict[str, Any],
        query: Optional["BaseQuery"] = None,
        collection: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if collection is None:
            collection = field + "s"
        pipeline: List[Dict[str, Any]] = [{"$match": condition}]
        if query is not None:
            if query.sort is not None:
                pipeline.append({"$sort": {"_id", query.sort}})
            if query.skip is not None:
                pipeline.append({"$skip": query.skip})
            if query.limit is not None:
                pipeline.append({"$limit": query.limit})
        pipeline += [
            {
                "$lookup": {
                    "from": collection,
                    "localField": field,
                    "foreignField": "_id",
                    "as": field,
                }
            },
            {"$addFields": {field: {"$arrayElemAt": ["$" + field, 0]}}},
        ]
        return pipeline

    @classmethod
    def cursor_find(
        cls: MotorAsyncIODocument,
        condition: Dict[str, Any],
        query: Optional["BaseQuery"] = None,
    ) -> AsyncIOMotorCursor:
        cursor = cls.find(condition)
        if query is not None:
            if query.sort is not None:
                cursor = cursor.sort("_id", query.sort)
            if query.skip is not None:
                cursor = cursor.skip(query.skip)
            if query.limit is not None:
                cursor = cursor.limit(query.limit)
        return cursor

    @classmethod
    def cursor_join(
        cls,
        field: str,
        condition: Dict[str, Any],
        query: Optional["BaseQuery"] = None,
        collection: Optional[str] = None,
    ) -> AsyncIOMotorCursor:
        pipeline = cls.generate_join_pipeline(field, condition, query, collection)
        return cls.aggregate(pipeline)


class BaseORMModel(models.Model):
    class Meta:
        abstract = True

    id = fields.UUIDField(pk=True)

    created_at = fields.DatetimeField(null=True, auto_now_add=True)
    updated_at = fields.DatetimeField(null=True, auto_now=True)

    def __str__(self) -> str:
        return str({k: v for k, v in self.__dict__.items() if not k.startswith("_")})


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


async def url_pre_save(
    sender: "Type[URLMixin]",
    instance: "URLMixin",
    using_db: "Optional[BaseDBAsyncClient]",
    update_fields: List[str],
) -> None:
    if not instance.id:
        instance.id = uuid.uuid4()
    if not instance.url:
        instance.url = str(instance.id)


@lru_cache()
def init_models() -> None:
    Tortoise.init_models(["joj.horse.models"], "models")
