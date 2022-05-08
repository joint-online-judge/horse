import logging
from functools import lru_cache

logging.getLogger("aiocache.serializers").handlers = [
    logging.NullHandler()
]  # disable aiocache.serializers logger
from aiocache import caches
from aiocache.base import BaseCache

from joj.horse.config import settings
from joj.horse.utils.retry import retry_init


@lru_cache()
def init_cache() -> None:
    caches.set_config(
        {
            "default": {
                "cache": "aiocache.SimpleMemoryCache",
                "serializer": {"class": "aiocache.serializers.PickleSerializer"},
            },
            "redis": {
                "cache": "aiocache.RedisCache",
                "endpoint": settings.redis_host,
                "port": settings.redis_port,
                "password": settings.redis_password or None,
                "db": settings.redis_db_index,
                "timeout": 1,
                "serializer": {"class": "aiocache.serializers.PickleSerializer"},
            },
        }
    )


@lru_cache()
def get_cache(name: str) -> BaseCache:
    init_cache()
    return caches.get(name)


@lru_cache()
def get_redis_cache() -> BaseCache:
    return get_cache("redis")


@retry_init("Redis")
async def try_init_cache() -> None:
    init_cache()
    cache: BaseCache = caches.get("redis")
    await cache.acquire_conn()
