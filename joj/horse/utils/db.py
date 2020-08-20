from functools import lru_cache

# from pydantic_odm.db import MongoDBManager
from motor.motor_asyncio import AsyncIOMotorClient

from joj.horse.config import settings
from joj.horse.models.user import User
from joj.horse.models.domain import Domain


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
    client = AsyncIOMotorClient(settings.db_host, settings.db_port)
    db = client.get_database(settings.db_name)
    _init_collections(db)
    return db


def _init_collections(db):
    User.use(db)
    Domain.use(db)


@lru_cache()
async def ensure_indexes():
    await User.init_indexes()
    await Domain.init_indexes()
