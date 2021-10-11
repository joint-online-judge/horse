from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Any, AsyncGenerator, Dict

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette_context import context
from tenacity import retry
from tenacity.stop import stop_after_attempt
from tenacity.wait import wait_exponential
from tortoise import Tortoise
from uvicorn.config import logger

from joj.horse.config import get_settings, settings


@lru_cache()
def get_db_engine() -> AsyncEngine:
    db_url = "postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}".format(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_username,
        password=settings.db_password,
        database=settings.db_name,
    )
    engine = create_async_engine(db_url, future=True, echo=True)
    return engine


@asynccontextmanager
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    # if a session is created for the request, use it directly
    if context.exists() and "db_session" in context:
        try:
            yield context["db_session"]
        finally:
            pass
    # otherwise, create a new session
    else:
        session = AsyncSession(get_db_engine())
        try:
            yield session
        finally:
            await session.close()


async def db_session_dependency() -> AsyncGenerator[AsyncSession, None]:
    # create a session for each request
    async with db_session() as session:
        context["db_session"] = session
        yield session


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
    attempt_number = try_init_db.retry.statistics["attempt_number"]
    try:
        await init_tortoise()
    except Exception as e:
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
