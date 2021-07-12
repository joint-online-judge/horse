import asyncio
from typing import Any, AsyncGenerator, Generator

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from fastapi_jwt_auth import AuthJWT
from httpx import AsyncClient

from joj.horse import app as fastapi_app
from joj.horse import models
from joj.horse.models.permission import DefaultRole
from joj.horse.tests.utils.utils import (
    create_test_domain,
    create_test_user,
    validate_test_domain,
)


@pytest.yield_fixture(scope="session")
def event_loop(request: Any) -> Generator[asyncio.AbstractEventLoop, Any, Any]:
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


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
    await user.commit()
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
async def global_domain_1(
    client: AsyncClient, global_root_user: models.User
) -> models.Domain:
    data = {"url": "test_domain_1", "name": "test_domain_1"}
    response = await create_test_domain(client, global_root_user, data)
    return validate_test_domain(response, global_root_user, data)
