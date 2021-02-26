from bson import ObjectId

from joj.horse.utils.errors import UnprocessableEntityError


class DocumentMixin:
    @classmethod
    async def find_by_id(cls, _id):
        if not ObjectId.is_valid(_id):
            raise UnprocessableEntityError("Invalid ObjectId")
        return await cls.find_one({"_id": ObjectId(_id)})

    @classmethod
    def aggregate(cls, pipeline, **kwargs):
        return cls.collection.aggregate(pipeline, **kwargs)
