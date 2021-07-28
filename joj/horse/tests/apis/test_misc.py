import jwt
import pytest
from fastapi_jwt_auth import AuthJWT
from httpx import AsyncClient
from pytest_lazyfixture import lazy_fixture

from joj.horse import app, models
from joj.horse.tests.utils.utils import do_api_request
from joj.horse.utils.auth import auth_jwt_encode
from joj.horse.utils.version import get_git_version, get_version


@pytest.mark.asyncio
class TestMisc:
    @pytest.mark.parametrize("user", [lazy_fixture("global_root_user")])
    async def test_version(self, client: AsyncClient, user: models.User) -> None:
        url = app.url_path_for("version")
        response = await do_api_request(client, "GET", url, user)
        assert response.status_code == 200
        res = response.json()
        assert res["version"] == get_version()
        assert res["git"] == get_git_version()

    @pytest.mark.parametrize("user", [lazy_fixture("global_root_user")])
    async def test_jwt(self, client: AsyncClient, user: models.User) -> None:
        url = app.url_path_for("jwt")
        response = await do_api_request(client, "GET", url, user)
        assert response.status_code == 200
        res = response.json()
        res_jwt_dict = jwt.decode(res["jwt"], verify=False)
        header_jwt_dict = jwt.decode(
            auth_jwt_encode(auth_jwt=AuthJWT(), user=user, channel="jaccount"),
            verify=False,
        )
        assert res_jwt_dict["sub"] == header_jwt_dict["sub"]
        assert res_jwt_dict["type"] == header_jwt_dict["type"]
        assert res_jwt_dict["fresh"] == header_jwt_dict["fresh"]
        assert res_jwt_dict["name"] == header_jwt_dict["name"]
        assert res_jwt_dict["scope"] == header_jwt_dict["scope"]
        assert res_jwt_dict["channel"] == header_jwt_dict["channel"]

    async def test_jwt_unauthorized(self, client: AsyncClient) -> None:
        url = app.url_path_for("jwt")
        response = await client.request(method="GET", url=url)
        assert response.status_code == 401
        res = response.json()
        assert res["detail"] == "Unauthorized"
