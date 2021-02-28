from typing import Type

from bson import ObjectId
from umongo.document import DocumentImplementation
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument, MotorAsyncIOReference

from joj.horse.utils.errors import UnprocessableEntityError


class DocumentMixin:
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
            if isinstance(field, MotorAsyncIOReference):
                field._document = None
