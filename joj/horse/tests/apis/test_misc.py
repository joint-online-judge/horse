from typing import Dict

import jwt
from fastapi.testclient import TestClient

from joj.horse.apis.misc import router_prefix
from joj.horse.models.user import User
from joj.horse.utils.version import get_git_version, get_version


def test_version(client: TestClient) -> None:
    r = client.get(f"{router_prefix}/version")
    res = r.json()
    assert r.status_code == 200
    assert res["version"] == get_version()
    assert res["git"] == get_git_version()


def test_jwt(
    client: TestClient, test_user_token_headers: Dict[str, str], test_user: User
) -> None:
    r = client.get(f"{router_prefix}/jwt", headers=test_user_token_headers)
    res = r.json()
    assert r.status_code == 200
    res_jwt_dict = jwt.decode(res["jwt"], verify=False)
    header_jwt_dict = jwt.decode(
        test_user_token_headers["Authorization"][7:], verify=False
    )
    assert res_jwt_dict["sub"] == header_jwt_dict["sub"]
    assert res_jwt_dict["type"] == header_jwt_dict["type"]
    assert res_jwt_dict["fresh"] == header_jwt_dict["fresh"]
    assert res_jwt_dict["name"] == header_jwt_dict["name"]
    assert res_jwt_dict["scope"] == header_jwt_dict["scope"]
    assert res_jwt_dict["channel"] == header_jwt_dict["channel"]
    assert res_jwt_dict.get("csrf") == header_jwt_dict.get("csrf")
