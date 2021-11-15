import asyncio
import sys
from typing import Any, AsyncGenerator, Generator

import pytest
from asgi_lifespan import LifespanManager
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.util.concurrency import greenlet_spawn
from sqlalchemy_utils import drop_database

from joj.horse import models
from joj.horse.app import app as fastapi_app
from joj.horse.config import settings
from joj.horse.models.permission import DefaultRole
from joj.horse.tests.utils.utils import (
    GLOBAL_DOMAIN_COUNT,
    GLOBAL_PROBLEM_SET_COUNT,
    create_test_domain,
    create_test_problem_set,
    login_test_user,
    user_access_tokens,
    user_refresh_tokens,
    validate_test_domain,
    validate_test_problem_set,
    validate_test_user,
)
from joj.horse.utils.db import get_db_url
from joj.horse.utils.logger import init_logging


@pytest.fixture(scope="session", autouse=True)
async def postgres(request: Any) -> None:
    init_logging(test=True)
    settings.db_name += "_test"
    settings.db_echo = False
    db_url = get_db_url()
    try:
        await greenlet_spawn(drop_database, db_url)
    except Exception:
        pass
    request.addfinalizer(lambda: asyncio.run(greenlet_spawn(drop_database, db_url)))


@pytest.yield_fixture(scope="session")
def event_loop(request: Any) -> Generator[asyncio.AbstractEventLoop, Any, Any]:
    loop = asyncio.get_event_loop_policy().get_event_loop()
    yield loop
    # loop.close()


@pytest.fixture(scope="session")
async def app() -> AsyncGenerator[FastAPI, Any]:
    async with LifespanManager(fastapi_app):
        yield fastapi_app


@pytest.fixture(scope="session")
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, Any]:
    async with AsyncClient(app=app, base_url="http://testserver") as c:
        yield c


async def login_and_validate_user(client: AsyncClient, username: str) -> models.User:
    response = await login_test_user(client, username)
    user, access_token, refresh_token = await validate_test_user(response, username)
    user_access_tokens[user.id] = access_token
    user_refresh_tokens[user.id] = refresh_token
    return user


@pytest.fixture(scope="session")
@pytest.mark.depends(on=["TestAuthRegister"])
async def global_root_user(client: AsyncClient) -> models.User:
    user = await login_and_validate_user(client, "global_root_user")
    user.role = DefaultRole.ROOT
    await user.save_model()
    return await login_and_validate_user(client, "global_root_user")


@pytest.fixture(scope="session")
async def global_domain_root_user(client: AsyncClient) -> models.User:
    return await login_and_validate_user(client, "global_domain_root_user")


@pytest.fixture(scope="session")
async def global_domain_user(client: AsyncClient) -> models.User:
    return await login_and_validate_user(client, "global_domain_user")


@pytest.fixture(scope="session")
async def global_guest_user(client: AsyncClient) -> models.User:
    return await login_and_validate_user(client, "global_guest_user")


def global_domain_factory(domain_id: int) -> Any:
    async def global_domain(
        client: AsyncClient, global_root_user: models.User
    ) -> models.Domain:
        domain_name = f"test_domain_{domain_id}"
        data = {"name": domain_name, "url": domain_name}
        response = await create_test_domain(client, global_root_user, data)
        return await validate_test_domain(response, global_root_user, data)

    return global_domain


for i in range(GLOBAL_DOMAIN_COUNT):
    name = f"global_domain_{i}"
    fn = pytest.fixture(scope="session", name=name)(global_domain_factory(i))
    setattr(sys.modules[__name__], "{}_func".format(name), fn)


@pytest.fixture(scope="session")
async def global_domain(global_domain_0: models.Domain) -> models.Domain:
    return global_domain_0


def global_problem_set_factory(problem_set_id: int) -> Any:
    async def global_problem_set(
        client: AsyncClient,
        global_domain: models.Domain,
        global_root_user: models.User,
    ) -> models.ProblemSet:
        title = f"test_problem_set_{problem_set_id}"
        data = {"title": title, "url": title}
        response = await create_test_problem_set(
            client, global_domain, global_root_user, data
        )
        return await validate_test_problem_set(
            response, global_domain, global_root_user, data
        )

    return global_problem_set


for i in range(GLOBAL_PROBLEM_SET_COUNT):
    name = f"global_problem_set_{i}"
    fn = pytest.fixture(scope="session", name=name)(global_problem_set_factory(i))
    setattr(sys.modules[__name__], "{}_func".format(name), fn)
