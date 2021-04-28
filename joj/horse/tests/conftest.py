from typing import Any, Dict, Generator

import pytest
from fastapi.testclient import TestClient
from fastapi_jwt_auth import AuthJWT

from joj.horse import app
from joj.horse.config import settings
from joj.horse.models.user import User
from joj.horse.utils.auth import auth_jwt_encode

settings.db_name += "-test"

from joj.horse.tests.utils.utils import create_test_user


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, Any, Any]:
    with TestClient(app) as c:
        yield c


import asyncio


@pytest.fixture(scope="module")
def test_user() -> User:
    loop = asyncio.get_event_loop()
    user = loop.run_until_complete(create_test_user())
    return user


@pytest.fixture(scope="module")
def test_user_token_headers(test_user: User) -> Dict[str, str]:
    access_jwt = auth_jwt_encode(auth_jwt=AuthJWT(), user=test_user, channel="jaccount")
    return {"Authorization": f"Bearer {access_jwt}"}
