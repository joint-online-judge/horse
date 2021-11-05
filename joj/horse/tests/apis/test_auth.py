import pytest
from httpx import AsyncClient
from pytest_lazyfixture import lazy_fixture

from joj.horse import apis
from joj.horse.models.permission import DefaultRole
from joj.horse.models.user import User
from joj.horse.tests.utils.utils import (
    create_test_user,
    do_api_request,
    get_base_url,
    get_data_from_response,
    user_access_tokens,
    user_refresh_tokens,
)

base_auth_url = get_base_url(apis.auth)
base_user_url = get_base_url(apis.user)
base_domain_url = get_base_url(apis.domains)
base_problems_url = get_base_url(apis.problems)


@pytest.mark.asyncio
@pytest.mark.depends(name="TestAuthRegister", on="TestUtils")
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
        response = await create_test_user(client, username)
        res = get_data_from_response(response)
        assert res["accessToken"]
        assert res["refreshToken"]
        assert res["tokenType"] == "bearer"


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


@pytest.mark.asyncio
@pytest.mark.depends(name="TestAuthToken", on=["TestAuthLogin"])
class TestAuthToken:
    @pytest.mark.parametrize("user", [lazy_fixture("global_root_user")])
    async def test_get_access_token(self, client: AsyncClient, user: User) -> None:
        url = f"{base_auth_url}/token"
        query = {"responseType": "json", "cookie": False}
        access_token = user_access_tokens[user.id]
        headers = {"Authorization": f"Bearer {access_token}"}
        response = await do_api_request(
            client, "GET", url, user, query=query, headers=headers
        )
        res = get_data_from_response(response)
        assert res["accessToken"] == access_token
        assert res["tokenType"] == "bearer"

    @pytest.mark.parametrize("user", [lazy_fixture("global_root_user")])
    async def test_get_refresh_token(self, client: AsyncClient, user: User) -> None:
        url = f"{base_auth_url}/token"
        query = {"responseType": "json", "cookie": False}
        refresh_token = user_refresh_tokens[user.id]
        headers = {"Authorization": f"Bearer {refresh_token}"}
        response = await do_api_request(
            client, "GET", url, user, query=query, headers=headers
        )
        res = get_data_from_response(response)
        assert res["refreshToken"] == refresh_token
        assert res["tokenType"] == "bearer"

    @pytest.mark.parametrize("user", [lazy_fixture("global_root_user")])
    async def test_refresh(self, client: AsyncClient, user: User) -> None:
        url = f"{base_auth_url}/refresh"
        query = {"responseType": "json", "cookie": False}
        refresh_token = user_refresh_tokens[user.id]
        headers = {"Authorization": f"Bearer {refresh_token}"}
        response = await do_api_request(
            client, "POST", url, user, query=query, headers=headers
        )
        res = get_data_from_response(response)
        assert res["accessToken"]
        assert res["refreshToken"]
        assert res["tokenType"] == "bearer"
