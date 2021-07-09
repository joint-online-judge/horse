import asyncio
from typing import Any, AsyncGenerator, Dict, Generator

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from fastapi_jwt_auth import AuthJWT
from httpx import AsyncClient

from joj.horse import app as fastapi_app
from joj.horse.models.permission import DefaultRole
from joj.horse.models.user import User
from joj.horse.tests.utils.utils import create_test_user
from joj.horse.utils.auth import auth_jwt_encode


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
async def global_root_user(app: FastAPI) -> User:
    user = await create_test_user()
    user.role = DefaultRole.ROOT
    await user.commit()
    return user


@pytest.fixture(scope="session")
async def global_domain_root_user(app: FastAPI) -> User:
    return await create_test_user()


@pytest.fixture(scope="session")
async def global_domain_user(app: FastAPI) -> User:
    return await create_test_user()


@pytest.fixture(scope="session")
async def global_guest_user(app: FastAPI) -> User:
    return await create_test_user()


@pytest.fixture(scope="session")
def global_test_user() -> User:
    loop = asyncio.get_event_loop()
    user = loop.run_until_complete(create_test_user())
    return user


@pytest.fixture(scope="session")
def global_test_user_token_headers(global_test_user: User) -> Dict[str, str]:
    access_jwt = auth_jwt_encode(
        auth_jwt=AuthJWT(), user=global_test_user, channel="jaccount"
    )
    return {"Authorization": f"Bearer {access_jwt}"}


@pytest.fixture(scope="module")
def test_user() -> User:
    loop = asyncio.get_event_loop()
    user = loop.run_until_complete(create_test_user())
    return user


@pytest.fixture(scope="module")
def test_user_token_headers(test_user: User) -> Dict[str, str]:
    access_jwt = auth_jwt_encode(auth_jwt=AuthJWT(), user=test_user, channel="jaccount")
    return {"Authorization": f"Bearer {access_jwt}"}
