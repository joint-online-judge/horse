from typing import Dict

from fastapi.testclient import TestClient

from joj.horse.apis import user
from joj.horse.models.user import User
from joj.horse.tests.utils.utils import get_base_url

base_url = get_base_url(user)


def test_get_user(
    client: TestClient, test_user_token_headers: Dict[str, str], test_user: User
) -> None:
    r = client.get(base_url, headers=test_user_token_headers)
    res = r.json()
    assert r.status_code == 200
    assert res["scope"] == "sjtu"
    assert res["uname"] == test_user.uname
    assert res["student_id"] == test_user.student_id
    assert res["real_name"] == test_user.real_name
    assert res["login_ip"] == test_user.login_ip


def test_empty_get_user_problems(
    client: TestClient, test_user_token_headers: Dict[str, str], test_user: User
) -> None:
    r = client.get(f"{base_url}/problems", headers=test_user_token_headers)
    res = r.json()
    assert r.status_code == 200
    assert not res
