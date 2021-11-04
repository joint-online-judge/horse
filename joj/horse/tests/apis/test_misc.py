import jwt
import pytest
from httpx import AsyncClient
from pytest_lazyfixture import lazy_fixture

from joj.horse import models
from joj.horse.app import app
from joj.horse.config import settings
from joj.horse.tests.utils.utils import do_api_request, user_access_tokens
from joj.horse.utils.version import get_git_version, get_version


@pytest.mark.asyncio
@pytest.mark.depends(name="TestMisc", on=["TestAuthLogin"])
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
        url = app.url_path_for("jwt_decoded")
        response = await do_api_request(client, "GET", url, user)
        assert response.status_code == 200
        res = response.json()
        assert "data" in res
        res_jwt_dict = res["data"]
        access_token = user_access_tokens[user.id]
        header_jwt_dict = jwt.decode(
            access_token,
            key=settings.jwt_secret,
            verify=False,
            algorithms=[settings.jwt_algorithm],
        )
        for key in [
            "sub",
            "iat",
            "nbf",
            "exp",
            "type",
            "fresh",
            "csrf",
            "category",
            "username",
            "email",
            "student_id",
            "real_name",
            "role",
            "oauth_name",
            "is_active",
        ]:
            assert res_jwt_dict.get(key) == header_jwt_dict.get(key)

    async def test_jwt_decoded_unauthorized(self, client: AsyncClient) -> None:
        url = app.url_path_for("jwt_decoded")
        response = await client.request(method="GET", url=url)
        assert response.status_code == 401
        res = response.json()
        assert res["detail"] == "Unauthorized"
