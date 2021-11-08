from functools import lru_cache

from aiocache import caches
from aiocache.base import BaseCache

from joj.horse.config import settings

# from tenacity import retry
# from tenacity.stop import stop_after_attempt
# from tenacity.wait import wait_fixed
# from loguru import logger


@lru_cache()
def init_cache() -> None:
    caches.set_config(
        {
            "default": {
                "cache": "aiocache.SimpleMemoryCache",
                "serializer": {"class": "aiocache.serializers.PickleSerializer"},
            },
            "session": {
                "cache": "aiocache.RedisCache",
                "endpoint": settings.redis_host,
                "port": settings.redis_port,
                "timeout": 1,
                "serializer": {"class": "aiocache.serializers.PickleSerializer"},
            },
        }
    )


@lru_cache()
def get_cache(name: str) -> BaseCache:
    init_cache()
    return caches.get(name)


# @retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
# async def test_cache() -> None:
#     attempt_number = test_cache.retry.statistics["attempt_number"]
#     if attempt_number == 1:
#         logger.info("Starting redis cache connection.")
#     try:
#         init_cache()
#         cache: BaseCache = caches.get("session")
#         await cache.acquire_conn()
#     except Exception as e:
#         max_attempt_number = test_cache.retry.stop.max_attempt_number
#         msg = "Redis connection failed (%d/%d)" % (attempt_number, max_attempt_number)
#         if attempt_number < max_attempt_number:
#             msg += ", trying again after %d second." % test_cache.retry.wait.wait_fixed
#         else:
#             msg += "."
#         logger.warning(msg)
#         raise e
