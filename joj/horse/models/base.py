from typing import Any

from bson import ObjectId
from pydantic import BaseModel
from umongo.data_objects import Dict, List, Reference
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument

from joj.horse.utils.errors import UnprocessableEntityError


class DocumentMixin:
    __slots__ = ()

    id: ObjectId

    @classmethod
    async def find_by_id(cls: MotorAsyncIODocument, _id: str) -> Any:
        if not ObjectId.is_valid(_id):
            raise UnprocessableEntityError("Invalid ObjectId")
        return await cls.find_one({"_id": ObjectId(_id)})

    @classmethod
    def aggregate(cls: MotorAsyncIODocument, pipeline: Any, **kwargs: Any) -> Any:
        return cls.collection.aggregate(pipeline, **kwargs)

    def unfetch_all(self: MotorAsyncIODocument) -> None:
        for field in self._data.values():
            if isinstance(field, Reference):
                field._document = None
            if isinstance(field, List):
                for item in field:
                    if isinstance(item, Reference):
                        item._document = None
            if isinstance(field, Dict):
                for key, value in field:
                    if isinstance(key, Reference):
                        key._document = None
                    if isinstance(value, Reference):
                        value._document = None

    def update_from_schema(self: MotorAsyncIODocument, schema: BaseModel) -> None:
        self.update({k: v for k, v in schema.__dict__.items() if v is not None})
