from typing import Dict

import pytest
from fastapi_jwt_auth import AuthJWT
from httpx import AsyncClient
from pytest_lazyfixture import lazy_fixture

from joj.horse import apis
from joj.horse.app import app
from joj.horse.models.user import User
from joj.horse.tests.utils.utils import (
    do_api_request,
    get_base_url,
    validate_user_profile,
)

base_user_url = get_base_url(apis.users)
base_domain_url = get_base_url(apis.domains)

BUILD_PATH = "build2"


@pytest.mark.asyncio
@pytest.mark.depends(name="TestUserGet", on=["TestAuthLogin"])
class TestUserGet:
    @pytest.mark.parametrize(
        "user",
        [
            lazy_fixture("global_root_user"),
            lazy_fixture("global_domain_root_user"),
            lazy_fixture("global_domain_user"),
            lazy_fixture("global_guest_user"),
        ],
    )
    async def test_global_users(self, client: AsyncClient, user: User) -> None:
        response = await do_api_request(
            client,
            "GET",
            f"{base_user_url}/me",
            user,
        )
        validate_user_profile(response, user)
        # assert r.status_code == 200
        # res = r.json()
        # assert res["errorCode"] == ErrorCode.Success
        # res = res["data"]
        # assert res["username"] == user.username
        # assert res["email"] == user.email
        # assert res["studentId"] == user.student_id
        # assert res["realName"] == user.real_name
        # assert res["loginIp"] == user.login_ip


@pytest.mark.asyncio
@pytest.mark.depends(name="TestUserGetError", on=["TestAuthLogin"])
class TestUserGetError:
    # @pytest.mark.parametrize("user", [lazy_fixture("global_root_user")])
    # async def test_scope_error_user(self, client: AsyncClient, user: User) -> None:
    #     user_copy = copy(user)
    #     user_copy.scope = "error"
    #     headers = generate_auth_headers(user_copy)
    #     r = await client.get(base_user_url, headers=headers)
    #     assert r.status_code == 401

    @pytest.mark.parametrize("user", [lazy_fixture("global_root_user")])
    async def test_jwt_format_error_user(self, client: AsyncClient, user: User) -> None:
        access_token = AuthJWT().create_access_token(subject=str(user.id))
        headers = {"Authorization": f"Bearer {access_token}"}
        r = await client.get(f"{base_user_url}/me", headers=headers)
        assert r.status_code == 401


@pytest.mark.asyncio
@pytest.mark.depends(name="TestUserEdit", on=["TestUserGet"])
class TestUserEdit:
    url_base = "update_current_user"

    async def validate_update(
        self, client: AsyncClient, user: User, data: Dict[str, str]
    ) -> None:
        url = app.url_path_for(self.url_base)
        response = await do_api_request(
            client,
            "PATCH",
            url,
            user,
            data=data,
        )
        user.update_from_dict(data)
        validate_user_profile(response, user)

    @pytest.mark.parametrize(
        "user",
        [
            lazy_fixture("global_root_user"),
            lazy_fixture("global_domain_root_user"),
            lazy_fixture("global_domain_user"),
            lazy_fixture("global_guest_user"),
        ],
    )
    async def test_update_all(self, client: AsyncClient, user: User) -> None:
        patch_data = {
            "gravatar": "shili2018@fudan.test.test.edu",
            # "real_name": "Shi Li Li",
        }
        await self.validate_update(client, user, patch_data)

    # @pytest.mark.parametrize(
    #     "user",
    #     [
    #         lazy_fixture("global_root_user"),
    #         lazy_fixture("global_domain_root_user"),
    #         lazy_fixture("global_domain_user"),
    #         lazy_fixture("global_guest_user"),
    #     ],
    # )
    # async def test_update_real_name(self, client: AsyncClient, user: User) -> None:
    #     patch_data = {"real_name": "xm"}
    #     await self.validate_update(client, user, patch_data)

    # @pytest.mark.parametrize(
    #     "user",
    #     [
    #         lazy_fixture("global_root_user"),
    #         lazy_fixture("global_domain_root_user"),
    #         lazy_fixture("global_domain_user"),
    #         lazy_fixture("global_guest_user"),
    #     ],
    # )
    # async def test_update_gravatar(self, client: AsyncClient, user: User) -> None:
    #     patch_data = {"gravatar": "xm@admire.com"}
    #     await self.validate_update(client, user, patch_data)

    @pytest.mark.parametrize(
        "user",
        [
            lazy_fixture("global_root_user"),
            lazy_fixture("global_domain_root_user"),
            lazy_fixture("global_domain_user"),
            lazy_fixture("global_guest_user"),
        ],
    )
    async def test_update_none(self, client: AsyncClient, user: User) -> None:
        patch_data: Dict[str, str] = {}
        await self.validate_update(client, user, patch_data)


# def test_get_user_domains(
#     client: TestClient, test_user_token_headers: Dict[str, str], test_user: User
# ) -> None:
#     global NEW_DOMAIN
#     r = client.post(
#         f"{base_domain_url}",
#         json=jsonable_encoder(domain),
#         headers=test_user_token_headers,
#     )
#     assert r.status_code == 200
#     r = client.get(f"{base_user_url}/domains", headers=test_user_token_headers)
#     assert r.status_code == 200
#     res = r.json()
#     assert len(res) == 1
#     res = res[0]
#     NEW_DOMAIN = res["domain"]
#     assert res["domain"]["id"]
#     assert res["domain"]["url"] == domain.url
#     assert res["domain"]["name"] == domain.name
#     assert res["domain"]["bulletin"] == domain.bulletin
#     assert res["domain"]["gravatar"] == domain.gravatar
#     assert res["domain"]["owner"] == str(test_user.id)


# def test_get_user_problems(
#     client: TestClient, test_user_token_headers: Dict[str, str], test_user: User
# ) -> None:
#     r = client.post(
#         f"{base_problems_url}",
#         json=jsonable_encoder(problem),
#         headers=test_user_token_headers,
#     )
#     assert r.status_code == 200
#     r = client.get(f"{base_user_url}/problems", headers=test_user_token_headers)
#     assert r.status_code == 200
#     res = r.json()
#     assert res["errorCode"] == ErrorCode.Success
#     res = res["data"]["results"]
#     assert len(res) == 1
#     res = res[0]
#     # assert res["domain"] == NEW_DOMAIN["id"]
#     assert res["title"] == problem.title
#     assert res["content"] == problem.content
#     assert res["languages"] == problem.languages
#     assert res["owner"] == str(test_user.id)
#     assert res["num_submit"] == 0
#     assert res["num_accept"] == 0
#     assert res["data"] is None
#     assert res["data_version"] == 2
