from functools import lru_cache
from typing import List, Type

from motor.motor_asyncio import AsyncIOMotorClient
from umongo.frameworks.motor_asyncio import MotorAsyncIODocument, MotorAsyncIOInstance
from uvicorn.config import logger

from joj.horse.config import settings

instance = MotorAsyncIOInstance()


@lru_cache()
def get_db():
    logger.info("Starting mongodb connection.")
    client = AsyncIOMotorClient(settings.db_host, settings.db_port)
    db = client.get_database(settings.db_name)
    instance.set_db(db)
    return db


from joj.horse import models

collections: List[Type[MotorAsyncIODocument]] = [
    models.User,
    models.Domain,
    models.DomainRole,
    models.DomainUser,
    models.Record,
    models.Problem,
    models.ProblemSet,
]


async def ensure_indexes():
    for model in collections:
        logger.info('Ensure indexes for "%s".' % model.opts.collection_name)
        await model.ensure_indexes()
