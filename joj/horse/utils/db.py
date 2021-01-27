from functools import lru_cache
from typing import List, Type

# from pydantic_odm.db import MongoDBManager
from motor.motor_asyncio import AsyncIOMotorClient
from uvicorn.config import logger

from joj.horse.config import settings
from joj.horse.models import *
from joj.horse.odm import Document


@lru_cache()
def get_db():
    # db_manager = await MongoDBManager({
    #     'default': {
    #         'NAME': settings.db_name,
    #         'HOST': settings.db_host,
    #         'PORT': settings.db_port,
    #     }
    # }).init_connections()
    # db = db_manager.databases.get('default')
    # print(asyncio.get_running_loop())
    logger.info("Starting mongodb connection.")
    client = AsyncIOMotorClient(settings.db_host, settings.db_port)
    db = client.get_database(settings.db_name)
    _init_collections(db)
    return db


collections: List[Type[Document]] = [
    Domain,
    DomainRole,
    DomainUser,
    Problem,
    ProblemSet,
    Record,
    User,
]


def _init_collections(db):
    for model in collections:
        model.use(db)


async def ensure_indexes():
    for model in collections:
        logger.info("Ensure indexes for \"%s\"." % model.__mongo__.collection)
        await model.init_indexes()
