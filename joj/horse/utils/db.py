from functools import lru_cache

from motor.motor_asyncio import AsyncIOMotorClient

from joj.horse.config import settings
from joj.horse.models.user import User


def get_db():
    client = AsyncIOMotorClient(settings.db_host, settings.db_port)
    db = client.get_database(settings.db_name)
    return db


@lru_cache()
def init_collections():
    db = get_db()
    User.use(db)


@lru_cache()
async def ensure_indexes():
    await User.init_indexes()
