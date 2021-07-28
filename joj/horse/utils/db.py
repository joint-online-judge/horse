from functools import lru_cache
from typing import Any, Dict

from tenacity import retry
from tenacity.stop import stop_after_attempt
from tenacity.wait import wait_exponential
from tortoise import Tortoise
from tortoise.exceptions import OperationalError
from uvicorn.config import logger

from joj.horse.config import settings


@lru_cache()
def get_tortoise_config() -> Dict[str, Any]:
    tortoise_config = {
        "connections": {
            "default": {
                "engine": "tortoise.backends.asyncpg",
                "credentials": {
                    "host": settings.db_host,
                    "port": settings.db_port,
                    "user": settings.db_username,
                    "password": settings.db_password,
                    "database": settings.db_name,
                },
            },
        },
        "apps": {
            "models": {
                "models": ["joj.horse.models"],
                "default_connection": "default",
            }
        },
    }
    logger.info(
        "Tortoise-ORM engine: %s.",
        tortoise_config["connections"]["default"]["engine"],  # type: ignore
    )
    return tortoise_config


async def init_tortoise() -> None:
    tortoise_config = get_tortoise_config()
    try:
        await Tortoise.init(config=tortoise_config, _create_db=True, use_tz=True)
        logger.info("Database %s created.", settings.db_name)  # pragma: no cover
    except OperationalError:
        await Tortoise.init(config=tortoise_config, use_tz=True)
        logger.info("Database %s exists.", settings.db_name)

    logger.info("Tortoise-ORM connected.")
    if settings.debug:  # pragma: no cover
        logger.info("Tortoise-ORM generating schema.")
        await Tortoise.generate_schemas()


@retry(stop=stop_after_attempt(5), wait=wait_exponential(2))
async def try_init_db() -> None:
    attempt_number = try_init_db.retry.statistics["attempt_number"]
    try:
        await init_tortoise()
    except Exception as e:  # pragma: no cover
        max_attempt_number = try_init_db.retry.stop.max_attempt_number
        msg = "Tortoise-ORM: initialization failed ({}/{})".format(
            attempt_number, max_attempt_number
        )
        if attempt_number < max_attempt_number:
            msg += ", trying again after {} second.".format(2 ** attempt_number)
        else:
            msg += "."
        logger.error(e)
        logger.warning(msg)
        raise e
