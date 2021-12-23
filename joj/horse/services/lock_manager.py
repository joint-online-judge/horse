from functools import lru_cache
from typing import Any, Dict, List

from aioredlock import Aioredlock

from joj.horse.config import settings


@lru_cache
def get_redis_instances() -> List[Dict[str, Any]]:
    return [
        {
            "host": settings.redis_host,
            "port": settings.redis_port,
            "password": settings.redis_password,
            "db": settings.redis_db_index,
        }
    ]


@lru_cache()
def get_lock_manager() -> Aioredlock:
    return Aioredlock(get_redis_instances(), retry_delay_min=0.3, retry_delay_max=0.7)
