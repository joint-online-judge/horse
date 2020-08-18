from functools import lru_cache

from aiocache import caches
from aiocache.base import BaseCache

from joj.horse.config import settings


@lru_cache()
def init_cache():
    caches.set_config({
        'default': {
            'cache': "aiocache.SimpleMemoryCache",
            'serializer': {
                'class': "aiocache.serializers.PickleSerializer"
            }
        },
        'session': {
            'cache': "aiocache.RedisCache",
            'endpoint': settings.redis_host,
            'port': settings.redis_port,
            'timeout': 1,
            'serializer': {
                'class': "aiocache.serializers.PickleSerializer"
            }
        }
    })


@lru_cache()
def get_cache(name: str) -> BaseCache:
    init_cache()
    return caches.get(name)


def test_cache():
    init_cache()
    caches.get("default")
    caches.get("session")
