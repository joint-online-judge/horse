from typing import TYPE_CHECKING, Any, Dict, List, Optional

from bson import ObjectId
from pydantic import BaseModel
from umongo import data_objects
from umongo.frameworks.motor_asyncio import AsyncIOMotorCursor, MotorAsyncIODocument

from joj.horse.utils.errors import UnprocessableEntityError

if TYPE_CHECKING:
    from joj.horse.schemas.query import BaseQuery


class DocumentMixin:
    __slots__ = ()

    class Meta:
        strict = False

    id: ObjectId

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
        filter: Dict[str, Any],
        update: Dict[str, Any],
        **kwargs: Any
    ) -> AsyncIOMotorCursor:
        return cls.collection.update_many(filter, update, **kwargs)

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
