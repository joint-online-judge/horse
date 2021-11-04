import pytest
from httpx import AsyncClient
from pytest_lazyfixture import lazy_fixture

from joj.horse import apis
from joj.horse.models.permission import DefaultRole
from joj.horse.models.user import User
from joj.horse.tests.utils.utils import create_test_user, get_base_url
from joj.horse.utils.errors import ErrorCode

base_auth_url = get_base_url(apis.auth)
base_user_url = get_base_url(apis.user)
base_domain_url = get_base_url(apis.domains)
base_problems_url = get_base_url(apis.problems)


@pytest.mark.asyncio
@pytest.mark.depends(name="TestAuthRegister")
class TestAuthRegister:
    @pytest.mark.parametrize(
        "username",
        [
            "global_root_user",
            "global_domain_root_user",
            "global_domain_user",
            "global_guest_user",
        ],
    )
    async def test_global_users(self, client: AsyncClient, username: str) -> None:
        r = await create_test_user(client, username)
        assert r.status_code == 200
        res = r.json()
        assert res["error_code"] == ErrorCode.Success
        res = res["data"]
        assert res["access_token"]
        assert res["refresh_token"]
        assert res["token_type"] == "bearer"


@pytest.mark.asyncio
@pytest.mark.depends(name="TestAuthLogin", on=["TestAuthRegister"])
class TestAuthLogin:
    @pytest.mark.parametrize(
        "user",
        [
            lazy_fixture("global_root_user"),
            lazy_fixture("global_domain_root_user"),
            lazy_fixture("global_domain_user"),
            lazy_fixture("global_guest_user"),
        ],
    )
    async def test_global_users(self, user: User) -> None:
        # we login global users in pytest fixtures,
        # so do not need to do anything here
        assert user

    @pytest.mark.depends(on="test_global_users")
    async def test_root_role(self, global_root_user: User) -> None:
        assert global_root_user.role == DefaultRole.ROOT

    # @pytest.mark.depends(on="test_global_users")
    # async def test_root_refresh(self, client: AsyncClient, global_root_user: User):
    #     url = f"{base_auth_url}/refresh"
    #     query = {"response_type": "json", "cookie": False}
    #     response = await do_api_request(
    #         client, "GET", url, global_root_user, query=query
    #     )
    #     assert response.status_code == 200
    #     res = response.json()
    #     assert res["error_code"] == ErrorCode.Success
    #     res = res["data"]
    #     assert res["access_token"]
    #     assert res["refresh_token"]
    #     assert res["token_type"] == "bearer"
    #     user_access_tokens[global_root_user.id] = res["refresh_token"]
