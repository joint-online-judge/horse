import logging
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import AsyncGenerator

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.util.concurrency import greenlet_spawn
from sqlalchemy_utils import create_database, database_exists
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from starlette_context import context

from joj.horse.config import settings
from joj.horse.utils.retry import retry_init


@lru_cache()
def get_db_url() -> str:
    return "postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}".format(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_username,
        password=settings.db_password,
        database=settings.db_name,
    )


@lru_cache()
def get_db_engine() -> AsyncEngine:
    db_url = get_db_url()
    engine = create_async_engine(db_url, future=True, echo=settings.db_echo)
    logging.getLogger("sqlalchemy.engine.Engine").handlers = [logging.NullHandler()]
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


# noinspection PyBroadException
async def ensure_db() -> None:
    engine = get_db_engine()
    try:
        exists = await greenlet_spawn(database_exists, engine.url)
    except Exception:
        exists = False
    if not exists:  # pragma: no cover
        await greenlet_spawn(create_database, engine.url)
        logger.info("Database {} created.", settings.db_name)
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
            logger.info("SQLModel generated schema.")
    else:  # pragma: no cover
        logger.info("Database {} already exists.", settings.db_name)


@retry_init("SQLModel")
async def try_init_db() -> None:
    await ensure_db()
