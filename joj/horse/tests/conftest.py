from typing import Any, Dict, Generator

import pytest
from fastapi.testclient import TestClient

from joj.horse import app
from joj.horse.config import settings

settings.db_name += "-test"


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, Any, Any]:
    with TestClient(app) as c:
        yield c
