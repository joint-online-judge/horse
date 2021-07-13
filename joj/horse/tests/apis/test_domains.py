from typing import Dict

import pytest
from fastapi.encoders import jsonable_encoder
from httpx import AsyncClient, Response
from pytest_lazyfixture import lazy_fixture

from joj.horse import apis, models
from joj.horse.tests.utils.utils import (
    create_test_domain,
    generate_auth_headers,
    get_base_url,
    get_path_by_url_type,
    validate_test_domain,
)
from joj.horse.utils.errors import ErrorCode

base_user_url = get_base_url(apis.user)
base_domain_url = get_base_url(apis.domains)


# domain = schemas.DomainCreate(
#     url=random_lower_string(),
#     name=random_lower_string(),
#     bulletin=random_lower_string(),
#     gravatar=random_lower_string(),
# )
# data = jsonable_encoder(domain)
# domain_edit = schemas.DomainEdit(
#     name=random_lower_string(),
#     bulletin=random_lower_string(),
#     gravatar=random_lower_string(),
# )
# update_data = jsonable_encoder(domain_edit)
# NEW_DOMAIN = {}


@pytest.mark.asyncio
@pytest.mark.depends(name="TestDomainCreate", on=["TestUserGet"])
class TestDomainCreate:
    @pytest.mark.parametrize(
        "domain",
        [
            lazy_fixture("global_domain_no_url"),
            lazy_fixture("global_domain_with_url"),
            lazy_fixture("global_domain_with_all"),
        ],
    )
    async def test_global_domains(self, domain: models.Domain) -> None:
        pass

    @pytest.mark.depends(on="test_global_domains")
    async def test_url_not_unique(
        self, client: AsyncClient, global_root_user: models.User
    ) -> None:
        data = {
            "url": "test_domain_with_url",
            "name": "test_domain_with_url_not_unique",
        }
        response = await create_test_domain(client, global_root_user, data)
        assert response.status_code == 200
        res = response.json()
        assert res["error_code"] == ErrorCode.UrlNotUniqueError

    @pytest.mark.depends(on="test_global_domains")
    async def test_no_name(
        self, client: AsyncClient, global_root_user: models.User
    ) -> None:
        data = {"url": "test_domain_no_name"}
        response = await create_test_domain(client, global_root_user, data)
        assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.depends(name="TestDomainGet", on=["TestDomainCreate"])
class TestDomainGet:
    @pytest.mark.parametrize("user", [lazy_fixture("global_root_user")])
    @pytest.mark.parametrize(
        "domain",
        [
            lazy_fixture("global_domain_no_url"),
            lazy_fixture("global_domain_with_url"),
            lazy_fixture("global_domain_with_all"),
        ],
    )
    @pytest.mark.parametrize("url_type", ["url", "id"])
    async def test_global_domains(
        self,
        client: AsyncClient,
        user: models.User,
        domain: models.Domain,
        url_type: str,
    ) -> None:
        headers = generate_auth_headers(user)
        domain_path = get_path_by_url_type(domain, url_type)
        response = await client.get(f"{base_domain_url}/{domain_path}", headers=headers)
        validate_test_domain(response, user, domain)


@pytest.mark.asyncio
@pytest.mark.depends(name="TestDomainUpdate", on=["TestDomainGet"])
class TestDomainUpdate:
    @staticmethod
    async def api_helper(
        client: AsyncClient,
        user: models.User,
        domain: models.Domain,
        url_type: str,
        data: Dict[str, str],
    ) -> Response:
        domain_path = get_path_by_url_type(domain, url_type)
        headers = generate_auth_headers(user)
        response = await client.patch(
            f"{base_domain_url}/{domain_path}",
            json=jsonable_encoder(data),
            headers=headers,
        )
        return response

    @pytest.mark.parametrize("user", [lazy_fixture("global_root_user")])
    @pytest.mark.parametrize("url_type", ["url", "id"])
    async def test_update_all(
        self,
        client: AsyncClient,
        user: models.User,
        global_domain_with_url: models.Domain,
        url_type: str,
    ) -> None:
        data = {}
        for field in ["url", "name", "bulletin", "gravatar"]:
            data[field] = f"{user.uname}-{field}-{url_type}-update-all"
        response = await self.api_helper(
            client, user, global_domain_with_url, url_type, data
        )
        global_domain_with_url.update(data)
        validate_test_domain(response, user, global_domain_with_url)

    @pytest.mark.parametrize("user", [lazy_fixture("global_root_user")])
    @pytest.mark.parametrize("url_type", ["url", "id"])
    @pytest.mark.parametrize("field", ["url", "name", "bulletin", "gravatar"])
    async def test_update_one(
        self,
        client: AsyncClient,
        user: models.User,
        global_domain_with_url: models.Domain,
        url_type: str,
        field: str,
    ) -> None:
        data = {field: f"{user.uname}-{field}-{url_type}-update-one"}
        response = await self.api_helper(
            client, user, global_domain_with_url, url_type, data
        )
        global_domain_with_url.update(data)
        validate_test_domain(response, user, global_domain_with_url)

    @pytest.mark.depends(on=["test_update_all", "test_update_one"])
    async def test_url_not_unique(
        self,
        client: AsyncClient,
        global_root_user: models.User,
        global_domain_with_url: models.Domain,
        global_domain_with_all: models.Domain,
    ) -> None:
        data = {"url": global_domain_with_all.url}
        response = await self.api_helper(
            client, global_root_user, global_domain_with_url, "url", data
        )
        assert response.status_code == 200
        res = response.json()
        assert res["error_code"] == ErrorCode.UrlNotUniqueError


# def test_list_domains(
#     client: TestClient, test_user_token_headers: Dict[str, str], test_user: User
# ) -> None:
#     r = client.get(f"{base_domain_url}", headers=test_user_token_headers)
#     assert r.status_code == 200
#     res = r.json()
#     assert res["error_code"] == ErrorCode.Success
#     res = res["data"]["results"]
#     assert len(res) == 1
#     assert res[0] == NEW_DOMAIN


# def test_get_domain(
#     client: TestClient, test_user_token_headers: Dict[str, str], test_user: User
# ) -> None:
#     r = client.get(f"{base_domain_url}/{domain.url}", headers=test_user_token_headers)
#     assert r.status_code == 200
#     res = r.json()
#     assert res["error_code"] == ErrorCode.Success
#     res = res["data"]
#     assert NEW_DOMAIN["owner"] == res["owner"]["id"]
#     res["owner"] = NEW_DOMAIN["owner"]
#     assert res == NEW_DOMAIN


# def test_member_join_in_domain_expired(
#     client: TestClient,
#     test_user_token_headers: Dict[str, str],
#     global_test_user_token_headers: Dict[str, str],
#     test_user: User,
#     global_test_user: User,
# ) -> None:
#     r = client.get(
#         f"{base_domain_url}/{domain.url}/members/join",
#         headers=global_test_user_token_headers,
#     )
#     assert r.status_code == 200
#     res = r.json()
#     assert res["error_code"] == ErrorCode.DomainInvitationBadRequestError


# def test_update_domain(
#     client: TestClient, test_user_token_headers: Dict[str, str], test_user: User
# ) -> None:
#     r = client.patch(
#         f"{base_domain_url}/{domain.url}",
#         json=update_data,
#         headers=test_user_token_headers,
#     )
#     assert r.status_code == 200
#     res = r.json()
#     assert res["error_code"] == ErrorCode.Success
#     res = res["data"]
#     assert ObjectId.is_valid(res["id"])
#     assert res["url"] == domain.url
#     assert res["name"] == domain_edit.name
#     assert res["bulletin"] == domain_edit.bulletin
#     assert res["gravatar"] == domain_edit.gravatar
#     assert res["owner"] == str(test_user.id)


# def test_add_member_to_domain(
#     client: TestClient,
#     test_user_token_headers: Dict[str, str],
#     test_user: User,
#     global_test_user: User,
# ) -> None:
#     # add duplicate member
#     r = client.post(
#         f"{base_domain_url}/{domain.url}/members/{test_user.id}",
#         headers=test_user_token_headers,
#     )
#     assert r.status_code == 200
#     res = r.json()
#     assert res["error_code"] == ErrorCode.UserAlreadyInDomainBadRequestError
#     # add new member
#     r = client.post(
#         f"{base_domain_url}/{domain.url}/members/{global_test_user.id}",
#         headers=test_user_token_headers,
#     )
#     assert r.status_code == 200
#     res = r.json()
#     assert res["error_code"] == ErrorCode.Success
#     # add new duplicate member
#     r = client.post(
#         f"{base_domain_url}/{domain.url}/members/{global_test_user.id}",
#         headers=test_user_token_headers,
#     )
#     assert r.status_code == 200
#     res = r.json()
#     assert res["error_code"] == ErrorCode.UserAlreadyInDomainBadRequestError


# def test_list_members_in_domain(
#     client: TestClient,
#     test_user_token_headers: Dict[str, str],
#     test_user: User,
#     global_test_user: User,
# ) -> None:
#     r = client.get(
#         f"{base_domain_url}/{domain.url}/members", headers=test_user_token_headers
#     )
#     assert r.status_code == 200
#     res = r.json()
#     assert res["error_code"] == ErrorCode.Success
#     res = res["data"]["results"]
#     assert len(res) == 2
#     for item in res:
#         assert item["domain"] == NEW_DOMAIN["id"]
#         assert item["join_at"]
#         if item["user"]["id"] == str(test_user.id):
#             assert item["role"] == "root"
#         elif item["user"]["id"] == str(global_test_user.id):
#             assert item["role"] == "user"
#         else:
#             assert False, f"Unknown user id: {item['user']['id']}"


# def test_remove_member_from_domain(
#     client: TestClient,
#     test_user_token_headers: Dict[str, str],
#     test_user: User,
#     global_test_user: User,
# ) -> None:
#     r = client.delete(
#         f"{base_domain_url}/{domain.url}/members/{global_test_user.id}",
#         headers=test_user_token_headers,
#     )
#     assert r.status_code == 200
#     res = r.json()
#     assert res["error_code"] == ErrorCode.Success
#     # TODO: what about the last user / creator of the domain is deleted?
#     r = client.get(
#         f"{base_domain_url}/{domain.url}/members", headers=test_user_token_headers
#     )
#     assert r.status_code == 200
#     res = r.json()
#     assert res["error_code"] == ErrorCode.Success
#     res = res["data"]["results"]
#     assert len(res) == 1
#     res = res[0]
#     assert res["user"]["id"] == str(test_user.id)


# def test_member_join_in_domain(
#     client: TestClient,
#     test_user_token_headers: Dict[str, str],
#     global_test_user_token_headers: Dict[str, str],
#     test_user: User,
#     global_test_user: User,
# ) -> None:
#     # wrong invitation code
#     r = client.get(
#         f"{base_domain_url}/{domain.url}/members/join",
#         params={"invitation_code": "wrong"},
#         headers=global_test_user_token_headers,
#     )
#     assert r.status_code == 200
#     res = r.json()
#     assert res["error_code"] == ErrorCode.DomainInvitationBadRequestError
#     r = client.get(
#         f"{base_domain_url}/{domain.url}/members", headers=test_user_token_headers
#     )
#     assert r.status_code == 200
#     res = r.json()
#     assert res["error_code"] == ErrorCode.Success
#     res = res["data"]
#     assert len(res) == 1
#     # right invitation code
#     r = client.get(
#         f"{base_domain_url}/{domain.url}/members/join",
#         headers=global_test_user_token_headers,
#     )
#     assert r.status_code == 200
#     res = r.json()
#     assert res["error_code"] == ErrorCode.Success
#     r = client.get(
#         f"{base_domain_url}/{domain.url}/members", headers=test_user_token_headers
#     )
#     assert r.status_code == 200
#     res = r.json()
#     assert res["error_code"] == ErrorCode.Success
#     res = res["data"]["results"]
#     assert len(res) == 2
#     for item in res:
#         assert item["domain"] == NEW_DOMAIN["id"]
#         assert item["join_at"]
#         if item["user"]["id"] == str(test_user.id):
#             assert item["role"] == "root"
#         elif item["user"]["id"] == str(global_test_user.id):
#             assert item["role"] == "user"
#         else:
#             assert False, f"Unknown user id: {item['user']['id']}"
