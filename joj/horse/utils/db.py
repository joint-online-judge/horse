from functools import lru_cache

from motor.motor_asyncio import AsyncIOMotorClient

from joj.horse.config import settings
from joj.horse.models.user import User


@lru_cache()
def get_db():
    client = AsyncIOMotorClient(settings.db_host, settings.db_port)
    db = client.get_database(settings.db_name)
    _init_collections(db)
    return db


def _init_collections(db):
    User.use(db)


@lru_cache()
async def ensure_indexes():
    await User.init_indexes()
