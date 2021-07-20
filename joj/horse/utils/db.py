from tortoise import Tortoise
from tortoise.exceptions import OperationalError
from uvicorn.config import logger

from joj.horse.config import settings


async def init_tortoise() -> None:
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
    try:
        await Tortoise.init(config=tortoise_config, _create_db=True, use_tz=True)
        logger.info("Database %s created.", settings.db_name)
    except OperationalError:
        await Tortoise.init(config=tortoise_config, use_tz=True)
        logger.info("Database %s exists.", settings.db_name)

    logger.info("Tortoise-ORM started, %s, %s.", Tortoise._connections, Tortoise.apps)
    if settings.debug:
        logger.info("Tortoise-ORM generating schema.")
        await Tortoise.generate_schemas()
