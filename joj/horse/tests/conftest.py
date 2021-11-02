import asyncio
from typing import Any, AsyncGenerator, Generator

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import AsyncClient
from loguru import logger
from sqlalchemy.util.concurrency import greenlet_spawn
from sqlalchemy_utils import drop_database

from joj.horse import models
from joj.horse.app import app as fastapi_app
from joj.horse.config import settings
from joj.horse.models.permission import DefaultRole
from joj.horse.tests.utils.utils import (
    create_test_domain,
    create_test_user,
    validate_test_domain,
)
from joj.horse.utils.db import ensure_db, generate_schema, get_db_engine


@pytest.yield_fixture(scope="session")
def event_loop(request: Any) -> Generator[asyncio.AbstractEventLoop, Any, Any]:
    loop = asyncio.get_event_loop_policy().get_event_loop()
    yield loop
    # loop.close()


async def drop_db() -> None:
    engine = get_db_engine()
    await greenlet_spawn(drop_database, engine.url)
    logger.info("Database {} dropped.", settings.db_name)


@pytest.fixture(scope="session", autouse=True)
async def postgres(request: Any) -> None:
    settings.db_name += "_test"
    await ensure_db()
    await generate_schema()
    request.addfinalizer(lambda: asyncio.run(drop_db()))


@pytest.fixture(scope="session")
async def app() -> AsyncGenerator[FastAPI, Any]:
    async with LifespanManager(fastapi_app):
        yield fastapi_app


@pytest.fixture(scope="session")
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, Any]:
    async with AsyncClient(app=app, base_url="http://testserver") as c:
        yield c


@pytest.fixture(scope="session")
async def global_root_user(app: FastAPI) -> models.User:
    user = await create_test_user()
    user.role = DefaultRole.ROOT
    await user.save_model()
    return user


@pytest.fixture(scope="session")
async def global_domain_root_user(app: FastAPI) -> models.User:
    return await create_test_user()


@pytest.fixture(scope="session")
async def global_domain_user(app: FastAPI) -> models.User:
    return await create_test_user()


@pytest.fixture(scope="session")
async def global_guest_user(app: FastAPI) -> models.User:
    return await create_test_user()


@pytest.fixture(scope="session")
async def global_domain_no_url(
    client: AsyncClient, global_root_user: models.User
) -> models.Domain:
    data = {"name": "test_domain_no_url"}
    response = await create_test_domain(client, global_root_user, data)
    return await validate_test_domain(response, global_root_user, data)


@pytest.fixture(scope="session")
async def global_domain_with_url(
    client: AsyncClient, global_root_user: models.User
) -> models.Domain:
    data = {"url": "test_domain_with_url", "name": "test_domain_with_url"}
    response = await create_test_domain(client, global_root_user, data)
    return await validate_test_domain(response, global_root_user, data)


@pytest.fixture(scope="session")
async def global_domain_with_all(
    client: AsyncClient, global_root_user: models.User
) -> models.Domain:
    data = {
        "url": "test_domain_with_all",
        "name": "test_domain_with_all",
        "gravatar": "gravatar",
        "bulletin": "bulletin",
    }
    response = await create_test_domain(client, global_root_user, data)
    return await validate_test_domain(response, global_root_user, data)
