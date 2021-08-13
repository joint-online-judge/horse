from functools import lru_cache
from typing import Any, Dict

from tenacity import retry
from tenacity.stop import stop_after_attempt
from tenacity.wait import wait_exponential
from tortoise import Tortoise
from uvicorn.config import logger

from joj.horse.config import get_settings, settings


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
                "models": ["joj.horse.models", "aerich.models"],
                "default_connection": "default",
            }
        },
    }
    logger.info(
        "Tortoise-ORM engine: %s.",
        tortoise_config["connections"]["default"]["engine"],  # type: ignore
    )
    return tortoise_config


def __getattr__(name: str) -> Any:
    if name == "tortoise_config":
        get_settings()
        return get_tortoise_config()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


async def create() -> None:
    await Tortoise.init(config=get_tortoise_config(), _create_db=True, use_tz=True)
    logger.info("Database %s created.", settings.db_name)


async def init_tortoise() -> None:
    await Tortoise.init(config=get_tortoise_config(), use_tz=True)
    logger.info("Tortoise-ORM connected: %s.", settings.db_name)


async def generate_schema() -> None:
    await Tortoise.generate_schemas()
    logger.info("Tortoise-ORM generated schema.")


@retry(stop=stop_after_attempt(5), wait=wait_exponential(2))
async def try_init_db() -> None:
    attempt_number = try_init_db.retry.statistics["attempt_number"]  # type: ignore
    try:
        await init_tortoise()
    except Exception as e:
        max_attempt_number = try_init_db.retry.stop.max_attempt_number  # type: ignore
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
