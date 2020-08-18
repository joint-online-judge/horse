from functools import lru_cache

from motor.motor_asyncio import AsyncIOMotorClient

from joj.horse.config import settings


@lru_cache()
def get_db():
    print(settings)
    client = AsyncIOMotorClient(settings.db_host, settings.db_port)
