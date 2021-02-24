from bson import ObjectId


class DocumentMixin:
    @classmethod
    async def find_by_id(cls, _id):
        return await cls.find_one({"_id": ObjectId(_id)})
