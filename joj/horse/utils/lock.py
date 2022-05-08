from typing import AsyncGenerator

from aioredlock import Lock, LockError
from fastapi import Path
from loguru import logger

from joj.horse.services.lock_manager import get_lock_manager
from joj.horse.utils.errors import BizError, ErrorCode


async def lock_problem_config(problem: str = Path(...)) -> AsyncGenerator[Lock, None]:
    lock_manager = get_lock_manager()
    lock = None
    resource = f"problem:{problem}:config"
    try:
        logger.debug("redis lock {}", resource)
        lock = await lock_manager.lock(resource, lock_timeout=10)
        logger.debug("redis locked {}", resource)
        yield lock
    except LockError:
        raise BizError(ErrorCode.LockError, resource)
    finally:
        if lock is not None:
            logger.debug("redis unlock {}", resource)
            await lock_manager.unlock(lock)


async def lock_record_judger(record: str = Path(...)) -> AsyncGenerator[Lock, None]:
    lock_manager = get_lock_manager()
    lock = None
    resource = f"record:{record}:judger"
    try:
        logger.debug("redis lock {}", resource)
        lock = await lock_manager.lock(resource, lock_timeout=10)
        logger.debug("redis locked {}", resource)
        yield lock
    except LockError:
        raise BizError(ErrorCode.LockError, resource)
    finally:
        if lock is not None:
            logger.debug("redis unlock {}", resource)
            await lock_manager.unlock(lock)
