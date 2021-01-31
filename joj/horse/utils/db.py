from functools import lru_cache
from typing import List, Type

from bson import ObjectId
from motor.motor_asyncio import AsyncIOMotorClient
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument, MotorAsyncIOInstance
from uvicorn.config import logger

from joj.horse.config import settings

instance = MotorAsyncIOInstance()


class PydanticObjectId(str):
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if isinstance(v, str):
            v = ObjectId(v)
        elif not isinstance(v, ObjectId):
            raise TypeError('ObjectId required')
        return str(v)


@lru_cache()
def get_db():
    logger.info("Starting mongodb connection.")
    client = AsyncIOMotorClient(settings.db_host, settings.db_port)
    db = client.get_database(settings.db_name)
    instance.set_db(db)
    return db


from joj.horse.models import *

collections: List[Type[MotorAsyncIODocument]] = [
    User,
]


async def ensure_indexes():
    for model in collections:
        logger.info("Ensure indexes for \"%s\"." % model.opts.collection_name)
        await model.ensure_indexes()
