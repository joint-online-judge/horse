from bson import ObjectId
from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient

from joj.horse import schemas
from joj.horse.apis import domains, user
from joj.horse.models.user import User
from joj.horse.tests.utils.utils import get_base_url, random_lower_string
from joj.horse.utils.errors import ErrorCode

base_user_url = get_base_url(user)
base_domain_url = get_base_url(domains)


domain = schemas.DomainCreate(
    url=random_lower_string(),
    name=random_lower_string(),
    bulletin=random_lower_string(),
    gravatar=random_lower_string(),
)
data = jsonable_encoder(domain)
domain_edit = schemas.DomainEdit(
    name=random_lower_string(),
    bulletin=random_lower_string(),
    gravatar=random_lower_string(),
)
update_data = jsonable_encoder(domain_edit)
# NEW_DOMAIN = {}


# def test_create_domain(
#     client: TestClient, test_user_token_headers: Dict[str, str], test_user: User
# ) -> None:
#     global NEW_DOMAIN
#     r = client.post(f"{base_domain_url}", json=data, headers=test_user_token_headers)
#     assert r.status_code == 200
#     res = r.json()
#     assert res["error_code"] == ErrorCode.Success
#     res = res["data"]
#     NEW_DOMAIN = res
#     assert res["id"]
#     assert res["url"] == domain.url
#     assert res["name"] == domain.name
#     assert res["bulletin"] == domain.bulletin
#     assert res["gravatar"] == domain.gravatar
#     assert res["owner"] == str(test_user.id)


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
