from typing import Dict

from fastapi.testclient import TestClient

from joj.horse.apis.user import router_prefix
from joj.horse.models.user import User


def test_get_user(
    client: TestClient, test_user_token_headers: Dict[str, str], test_user: User
) -> None:
    r = client.get(f"{router_prefix}/user", headers=test_user_token_headers)
    res = r.json()
    assert r.status_code == 200
    assert res["scope"] == "sjtu"
    assert res["uname"] == test_user.uname
    assert res["student_id"] == test_user.student_id
    assert res["real_name"] == test_user.real_name
    assert res["login_ip"] == test_user.login_ip
