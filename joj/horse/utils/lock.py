from typing import AsyncGenerator

from aioredlock import Lock, LockError
from fastapi import Depends
from loguru import logger

from joj.horse import models
from joj.horse.services.lock_manager import get_lock_manager
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.parser import parse_problem


async def lock_problem_config(
    problem: models.Problem = Depends(parse_problem),
) -> AsyncGenerator[Lock, None]:
    lock_manager = get_lock_manager()
    lock = None
    resource = f"problem:{problem.id}:config"
    try:
        logger.info("redis lock {}", resource)
        lock = await lock_manager.lock(resource, lock_timeout=10)
        yield lock
    except LockError:
        raise BizError(ErrorCode.LockError, resource)
    finally:
        if lock is not None:
            logger.info("redis unlock {}", resource)
            await lock_manager.unlock(lock)
