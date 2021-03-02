from typing import Type

from bson import ObjectId
from umongo.data_objects import Dict, List, Reference
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument

from joj.horse.utils.errors import UnprocessableEntityError


class DocumentMixin:
    __slots__ = ()

    @classmethod
    async def find_by_id(cls: MotorAsyncIODocument, _id):
        if not ObjectId.is_valid(_id):
            raise UnprocessableEntityError("Invalid ObjectId")
        return await cls.find_one({"_id": ObjectId(_id)})

    @classmethod
    def aggregate(cls: MotorAsyncIODocument, pipeline, **kwargs):
        return cls.collection.aggregate(pipeline, **kwargs)

    def unfetch_all(self: MotorAsyncIODocument):
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
