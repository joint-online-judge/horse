from typing import Any, Dict, Tuple
from uuid import uuid4

import pytest
from httpx import AsyncClient, Response
from pytest_lazyfixture import lazy_fixture

from joj.horse import apis, models
from joj.horse.app import app
from joj.horse.models.permission import DefaultRole
from joj.horse.tests.utils.utils import (
    GLOBAL_DOMAIN_COUNT,
    create_test_domain,
    do_api_request,
    get_base_url,
    get_path_by_url_type,
    parametrize_global_domains,
    validate_response,
    validate_test_domain,
)
from joj.horse.utils.errors import ErrorCode

base_user_url = get_base_url(apis.user)
base_domain_url = get_base_url(apis.domains)


# domain = models.DomainCreate(
#     url=random_lower_string(),
#     name=random_lower_string(),
#     bulletin=random_lower_string(),
#     gravatar=random_lower_string(),
# )
# data = jsonable_encoder(domain)
# domain_edit = models.DomainEdit(
#     name=random_lower_string(),
#     bulletin=random_lower_string(),
#     gravatar=random_lower_string(),
# )
# update_data = jsonable_encoder(domain_edit)
# NEW_DOMAIN = {}


@pytest.mark.asyncio
@pytest.mark.depends(name="TestDomainCreate", on=["TestUserGet"])
class TestDomainCreate:
    @parametrize_global_domains
    async def test_global_domains(self, domain: models.Domain) -> None:
        pass

    @pytest.mark.depends(on="test_global_domains")
    async def test_no_url(
        self, client: AsyncClient, global_root_user: models.User
    ) -> None:
        data = {"name": "test_domain_no_url"}
        response = await create_test_domain(client, global_root_user, data)
        await validate_test_domain(response, global_root_user, data)

    @pytest.mark.depends(on="test_global_domains")
    async def test_with_all(
        self, client: AsyncClient, global_root_user: models.User
    ) -> None:
        data = {
            "url": "test_domain_with_all",
            "name": "test_domain_with_all",
            "gravatar": "gravatar",
            "bulletin": "bulletin",
        }
        response = await create_test_domain(client, global_root_user, data)
        await validate_test_domain(response, global_root_user, data)

    @pytest.mark.depends(on="test_global_domains")
    async def test_url_duplicate(
        self,
        client: AsyncClient,
        global_root_user: models.User,
        global_domain: models.Domain,
    ) -> None:
        # data = {
        #     "url": "test_domain_with_url",
        #     "name": "test_domain_with_url_duplicate",
        # }
        data = {
            "url": str(global_domain.url),
            "name": f"{global_domain.name}_duplicate",
        }
        response = await create_test_domain(client, global_root_user, data)
        validate_response(response, ErrorCode.IntegrityError)

    @pytest.mark.depends(on="test_global_domains")
    async def test_no_name(
        self, client: AsyncClient, global_root_user: models.User
    ) -> None:
        data = {"url": "test_domain_no_name"}
        response = await create_test_domain(client, global_root_user, data)
        assert response.status_code == 422

    @pytest.mark.depends(on="test_global_domains")
    async def test_url_uuid(
        self, client: AsyncClient, global_root_user: models.User
    ) -> None:
        data = {
            "url": uuid4(),
            "name": uuid4(),
        }
        response = await create_test_domain(client, global_root_user, data)
        assert response.status_code == 422

    @pytest.mark.depends(on="test_global_domains")
    async def test_url_invalid(
        self, client: AsyncClient, global_root_user: models.User
    ) -> None:
        data = {
            "url": "test_domain_invalid_url_@",
            "name": uuid4(),
        }
        response = await create_test_domain(client, global_root_user, data)
        assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.depends(name="TestDomainGet", on=["TestDomainCreate::test_global_domains"])
class TestDomainGet:
    url_base = "get_domain"

    @pytest.mark.parametrize("user", [lazy_fixture("global_root_user")])
    @parametrize_global_domains
    @pytest.mark.parametrize("url_type", ["url", "id"])
    async def test_global_domains(
        self,
        client: AsyncClient,
        user: models.User,
        domain: models.Domain,
        url_type: str,
    ) -> None:
        domain_path = get_path_by_url_type(domain, url_type)
        url = app.url_path_for(self.url_base, domain=domain_path)
        response = await do_api_request(client, "GET", url, user)
        await validate_test_domain(response, user, domain)

    @pytest.mark.parametrize("user", [lazy_fixture("global_root_user")])
    @pytest.mark.parametrize("domain", [lazy_fixture("global_domain_0")])
    async def test_domain_not_exist(
        self,
        client: AsyncClient,
        user: models.User,
        domain: models.Domain,
    ) -> None:
        url = app.url_path_for(self.url_base, domain=domain.url + "_not_exist")
        response = await do_api_request(client, "GET", url, user)
        assert response.status_code == 200
        res = response.json()
        assert res["errorCode"] == ErrorCode.DomainNotFoundError


@pytest.mark.asyncio
@pytest.mark.depends(
    name="TestDomainUpdate", on=["TestDomainCreate::test_global_domains"]
)
class TestDomainUpdate:
    url_base = "update_domain"

    async def validate_update(
        self,
        client: AsyncClient,
        user: models.User,
        domain: models.Domain,
        data: Dict[str, str],
    ) -> None:
        url = app.url_path_for(self.url_base, domain=domain.url)
        response = await do_api_request(client, "PATCH", url, user, data=data)
        domain.update_from_dict(data)
        await validate_test_domain(response, user, domain)

    @pytest.mark.parametrize("user", [lazy_fixture("global_root_user")])
    @pytest.mark.parametrize("domain", [lazy_fixture("global_domain_0")])
    async def test_update_all(
        self,
        client: AsyncClient,
        user: models.User,
        domain: models.Domain,
    ) -> None:
        data = {}
        for field in ["url", "name", "bulletin", "gravatar"]:
            data[field] = f"{user.username}-{field}-update-all"
        await self.validate_update(client, user, domain, data)

    @pytest.mark.parametrize("user", [lazy_fixture("global_root_user")])
    @pytest.mark.parametrize("domain", [lazy_fixture("global_domain_0")])
    @pytest.mark.parametrize("field", ["url", "name", "bulletin", "gravatar"])
    async def test_update_one(
        self,
        client: AsyncClient,
        user: models.User,
        domain: models.Domain,
        field: str,
    ) -> None:
        data = {field: f"{user.username}-{field}-update-one"}
        await self.validate_update(client, user, domain, data)

    @pytest.mark.depends(on=["test_update_all", "test_update_one"])
    async def test_url_duplicate(
        self,
        client: AsyncClient,
        global_root_user: models.User,
        global_domain_0: models.Domain,
        global_domain_1: models.Domain,
    ) -> None:
        data = {"url": global_domain_1.url}
        url = app.url_path_for(self.url_base, domain=global_domain_0.url)
        response = await do_api_request(
            client, "PATCH", url, global_root_user, data=data
        )
        assert response.status_code == 200
        res = response.json()
        assert res["errorCode"] == ErrorCode.IntegrityError


@pytest.mark.asyncio
@pytest.mark.depends(
    name="TestDomainDelete", on=["TestDomainCreate::test_global_domains"]
)
class TestDomainDelete:
    @pytest.mark.parametrize("domain", [lazy_fixture("global_domain_0")])
    @pytest.mark.parametrize("user", [lazy_fixture("global_root_user")])
    async def test_delete(
        self,
        client: AsyncClient,
        user: models.User,
        domain: models.Domain,
    ) -> None:
        url = app.url_path_for("delete_domain", domain=domain.url)
        response = await do_api_request(client, "DELETE", url, user)
        assert response.status_code == 200
        res = response.json()
        assert res["errorCode"] == ErrorCode.APINotImplementedError


@pytest.mark.asyncio
@pytest.mark.depends(on=["TestDomainCreate::test_global_domains"])
class TestDomainList:
    url = app.url_path_for("list_domains")

    async def list_domain_helper(
        self, client: AsyncClient, user: models.User, ordering: str
    ) -> Any:
        response = await do_api_request(
            client, "GET", self.url, user, {"ordering": ordering}
        )
        assert response.status_code == 200
        res = response.json()
        res = res["data"]
        assert res["count"] == GLOBAL_DOMAIN_COUNT + 2
        assert len(res["results"]) == GLOBAL_DOMAIN_COUNT + 2
        return res

    @pytest.mark.parametrize("user", [lazy_fixture("global_root_user")])
    async def test_list_domain_asc(
        self, client: AsyncClient, user: models.User
    ) -> None:
        await self.list_domain_helper(client, user, "name")

    @pytest.mark.parametrize("user", [lazy_fixture("global_root_user")])
    async def test_list_domain_desc(
        self, client: AsyncClient, user: models.User
    ) -> None:
        await self.list_domain_helper(client, user, "-name")

    @pytest.mark.parametrize("user", [lazy_fixture("global_root_user")])
    async def test_list_domain_illegal_field(
        self, client: AsyncClient, user: models.User
    ) -> None:
        response = await do_api_request(
            client, "GET", self.url, user, {"ordering": "error_field"}
        )
        assert response.status_code == 200
        res = response.json()
        assert res["errorCode"] == ErrorCode.IllegalFieldError


@pytest.mark.asyncio
@pytest.mark.depends(
    name="TestDomainUserAdd", on=["TestDomainCreate::test_global_domains"]
)
class TestDomainUserAdd:
    url_base = "add_domain_user"

    async def api_test_helper(
        self,
        client: AsyncClient,
        user: models.User,
        added_user: models.User,
        domain: models.Domain,
        role: str = "",
    ) -> Response:
        data = {"user": str(added_user.id)}
        if role:
            data["role"] = role
        url = app.url_path_for(self.url_base, domain=domain.url)
        response = await do_api_request(client, "POST", url, user, data=data)
        return response

    @staticmethod
    def validate_domain_user(
        response: Response, user: models.User, domain: models.Domain, role: str
    ) -> None:
        assert response.status_code == 200
        res = response.json()
        assert res["errorCode"] == ErrorCode.Success
        res = res["data"]
        assert res["id"] == str(user.id)
        assert res["domainId"] == str(domain.id)
        assert res["domainRole"] == role

    @pytest.mark.parametrize(
        "domain",
        [
            lazy_fixture("global_domain_0"),
            lazy_fixture("global_domain_1"),
        ],
    )
    async def test_site_root_add_domain_root(
        self,
        client: AsyncClient,
        global_root_user: models.User,
        global_domain_root_user: models.User,
        domain: models.Domain,
    ) -> None:
        response = await self.api_test_helper(
            client, global_root_user, global_domain_root_user, domain, "root"
        )
        self.validate_domain_user(response, global_domain_root_user, domain, "root")

    @pytest.mark.parametrize(
        "user,domain",
        [
            (lazy_fixture("global_root_user"), lazy_fixture("global_domain_0")),
            (
                lazy_fixture("global_domain_root_user"),
                lazy_fixture("global_domain_1"),
            ),
        ],
    )
    @pytest.mark.depends(on="test_site_root_add_domain_root")
    async def test_add_domain_default_user(
        self,
        client: AsyncClient,
        user: models.User,
        global_domain_user: models.User,
        domain: models.Domain,
    ) -> None:
        response = await self.api_test_helper(client, user, global_domain_user, domain)
        self.validate_domain_user(
            response, global_domain_user, domain, DefaultRole.USER
        )

    # @pytest.mark.depends(on="test_add_domain_default_user")
    # async def test_permission(
    #     self,
    #     client: AsyncClient,
    #     global_domain_user: models.User,
    #     global_guest_user: models.User,
    #     global_domain_0: models.Domain,
    # ) -> None:
    #     response = await self.api_test_helper(
    #         client, global_domain_user, global_guest_user, global_domain_0
    #     )
    #     assert response.status_code == 403

    @pytest.mark.depends(on="test_add_domain_default_user")
    async def test_duplicate(
        self,
        client: AsyncClient,
        global_root_user: models.User,
        global_domain_user: models.User,
        global_domain_0: models.Domain,
    ) -> None:
        response = await self.api_test_helper(
            client, global_root_user, global_domain_user, global_domain_0
        )
        assert response.status_code == 200
        res = response.json()
        assert res["errorCode"] == ErrorCode.UserAlreadyInDomainBadRequestError

    @pytest.mark.parametrize("domain", [lazy_fixture("global_domain_0")])
    @pytest.mark.depends(on="test_add_domain_default_user")
    async def test_not_exist_role(
        self,
        client: AsyncClient,
        global_root_user: models.User,
        global_domain_root_user: models.User,
        domain: models.Domain,
    ) -> None:
        response = await self.api_test_helper(
            client, global_root_user, global_domain_root_user, domain, "not_exist_role"
        )
        assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.depends(name="TestDomainUserGet", on=["TestDomainUserAdd"])
class TestDomainUserGet:
    url_base = "get_domain_user"

    async def test_global_users(self) -> None:
        pass


@pytest.mark.asyncio
@pytest.mark.depends(name="TestDomainUserRemove", on=["TestDomainUserGet"])
class TestDomainUserRemove:
    url_base = "remove_domain_user"

    async def test_site_root_remove_domain_root(
        self,
        client: AsyncClient,
        global_root_user: models.User,
        global_domain_root_user: models.User,
        global_domain_0: models.Domain,
    ) -> None:
        url = app.url_path_for(
            self.url_base,
            domain=global_domain_0.url,
            user=global_domain_root_user.id,
        )
        response = await do_api_request(client, "DELETE", url, global_root_user)
        assert response.status_code == 200
        res = response.json()
        assert res["errorCode"] == ErrorCode.Success

        url = app.url_path_for(
            TestDomainUserGet.url_base,
            domain=global_domain_0.url,
            user=global_domain_root_user.id,
        )
        response = await do_api_request(client, "GET", url, global_root_user)
        assert response.status_code == 200
        res = response.json()
        assert res["errorCode"] == ErrorCode.DomainUserNotFoundError


@pytest.mark.asyncio
@pytest.mark.depends(name="TestDomainTransfer", on=["TestDomainUserGet"])
class TestDomainTransfer:
    url_base = "transfer_domain"
    tasks: Dict[str, Tuple[str, str, ErrorCode]] = {
        "basic": (
            "global_root_user",
            "global_domain_root_user",
            ErrorCode.Success,
        ),
        "site_root": (
            "global_root_user",
            "global_root_user",
            ErrorCode.Success,
        ),
        "not_owner": (
            "global_domain_user",
            "global_domain_root_user",
            ErrorCode.DomainNotOwnerError,
        ),
        "to_self": (
            "global_root_user",
            "global_root_user",
            ErrorCode.DomainNotOwnerError,
        ),
        "to_not_root": (
            "global_root_user",
            "global_domain_user",
            ErrorCode.DomainNotRootError,
        ),
    }

    async def api_test_helper(
        self, request: Any, client: AsyncClient, domain: models.Domain, name: str
    ) -> None:
        task = self.tasks.get(name)
        assert task
        user, target_user, error_code = task
        user_model: models.User = request.getfixturevalue(user)
        target_user_model: models.User = request.getfixturevalue(target_user)
        url = app.url_path_for(self.url_base, domain=domain.url)
        data = {"target_user": str(target_user_model.id)}
        response = await do_api_request(client, "POST", url, user_model, data=data)
        if error_code == ErrorCode.Success:
            domain.owner_id = target_user_model.id
            await validate_test_domain(response, target_user_model, domain)
        else:
            assert response.status_code == 200
            res = response.json()
            assert res["errorCode"] == error_code

    async def test_basic(
        self,
        request: Any,
        client: AsyncClient,
        global_domain_1: models.Domain,
    ) -> None:
        await self.api_test_helper(request, client, global_domain_1, "basic")

    @pytest.mark.depends(on="test_basic")
    async def test_site_root(
        self,
        request: Any,
        client: AsyncClient,
        global_domain_1: models.Domain,
    ) -> None:
        await self.api_test_helper(request, client, global_domain_1, "site_root")

    @pytest.mark.parametrize("name", ["not_owner", "to_self", "to_not_root"])
    @pytest.mark.depends(on="test_site_root")
    async def test_errors(
        self,
        request: Any,
        client: AsyncClient,
        global_domain_1: models.Domain,
        name: str,
    ) -> None:
        await self.api_test_helper(request, client, global_domain_1, name)


# def test_list_domains(
#     client: TestClient, test_user_token_headers: Dict[str, str], test_user: User
# ) -> None:
#     r = client.get(f"{base_domain_url}", headers=test_user_token_headers)
#     assert r.status_code == 200
#     res = r.json()
#     assert res["errorCode"] == ErrorCode.Success
#     res = res["data"]["results"]
#     assert len(res) == 1
#     assert res[0] == NEW_DOMAIN


# def test_get_domain(
#     client: TestClient, test_user_token_headers: Dict[str, str], test_user: User
# ) -> None:
#     r = client.get(f"{base_domain_url}/{domain.url}", headers=test_user_token_headers)
#     assert r.status_code == 200
#     res = r.json()
#     assert res["errorCode"] == ErrorCode.Success
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
#     assert res["errorCode"] == ErrorCode.DomainInvitationBadRequestError


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
#     assert res["errorCode"] == ErrorCode.Success
#     res = res["data"]
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
#     assert res["errorCode"] == ErrorCode.UserAlreadyInDomainBadRequestError
#     # add new member
#     r = client.post(
#         f"{base_domain_url}/{domain.url}/members/{global_test_user.id}",
#         headers=test_user_token_headers,
#     )
#     assert r.status_code == 200
#     res = r.json()
#     assert res["errorCode"] == ErrorCode.Success
#     # add new duplicate member
#     r = client.post(
#         f"{base_domain_url}/{domain.url}/members/{global_test_user.id}",
#         headers=test_user_token_headers,
#     )
#     assert r.status_code == 200
#     res = r.json()
#     assert res["errorCode"] == ErrorCode.UserAlreadyInDomainBadRequestError


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
#     assert res["errorCode"] == ErrorCode.Success
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
#     assert res["errorCode"] == ErrorCode.Success
#     # TODO: what about the last user / creator of the domain is deleted?
#     r = client.get(
#         f"{base_domain_url}/{domain.url}/members", headers=test_user_token_headers
#     )
#     assert r.status_code == 200
#     res = r.json()
#     assert res["errorCode"] == ErrorCode.Success
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
#     assert res["errorCode"] == ErrorCode.DomainInvitationBadRequestError
#     r = client.get(
#         f"{base_domain_url}/{domain.url}/members", headers=test_user_token_headers
#     )
#     assert r.status_code == 200
#     res = r.json()
#     assert res["errorCode"] == ErrorCode.Success
#     res = res["data"]
#     assert len(res) == 1
#     # right invitation code
#     r = client.get(
#         f"{base_domain_url}/{domain.url}/members/join",
#         headers=global_test_user_token_headers,
#     )
#     assert r.status_code == 200
#     res = r.json()
#     assert res["errorCode"] == ErrorCode.Success
#     r = client.get(
#         f"{base_domain_url}/{domain.url}/members", headers=test_user_token_headers
#     )
#     assert r.status_code == 200
#     res = r.json()
#     assert res["errorCode"] == ErrorCode.Success
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
