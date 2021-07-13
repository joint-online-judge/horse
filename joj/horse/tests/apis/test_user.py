import pytest
from bson import ObjectId
from fastapi.encoders import jsonable_encoder
from httpx import AsyncClient
from pytest_lazyfixture import lazy_fixture

from joj.horse import apis, schemas
from joj.horse.models.permission import DefaultRole
from joj.horse.models.user import User
from joj.horse.tests.utils.utils import (
    generate_auth_headers,
    get_base_url,
    random_bool,
    random_lower_string,
)
from joj.horse.utils.errors import ErrorCode

base_user_url = get_base_url(apis.user)
base_domain_url = get_base_url(apis.domains)
base_problems_url = get_base_url(apis.problems)

# domain = schemas.DomainCreate(
#     url=random_lower_string(),
#     name=random_lower_string(),
#     bulletin=random_lower_string(),
#     gravatar=random_lower_string(),
# )
# problem = schemas.ProblemCreate(
#     domain=domain.url,
#     title=random_lower_string(),
#     content=random_lower_string(length=64),
#     data_version=2,
#     languages=[],
# )
# NEW_DOMAIN = {}

BUILD_PATH = "build2"


@pytest.mark.asyncio
@pytest.mark.depends(name="TestUserCreate")
class TestUserCreate:
    async def test_root_user(self, global_root_user: User) -> None:
        assert global_root_user.role == DefaultRole.ROOT


@pytest.mark.asyncio
@pytest.mark.depends(name="TestUserGet", on=["TestUserCreate"])
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
        headers = generate_auth_headers(user)
        r = await client.get(base_user_url, headers=headers)
        assert r.status_code == 200
        res = r.json()
        assert res["error_code"] == ErrorCode.Success
        res = res["data"]
        assert res["scope"] == "sjtu"
        assert res["uname"] == user.uname
        assert res["student_id"] == user.student_id
        assert res["real_name"] == user.real_name
        assert res["login_ip"] == user.login_ip


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
#     assert ObjectId.is_valid(res["id"])
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
#     assert res["error_code"] == ErrorCode.Success
#     res = res["data"]["results"]
#     assert len(res) == 1
#     res = res[0]
#     assert ObjectId.is_valid(res["id"])
#     # assert res["domain"] == NEW_DOMAIN["id"]
#     assert res["title"] == problem.title
#     assert res["content"] == problem.content
#     assert res["languages"] == problem.languages
#     assert res["owner"] == str(test_user.id)
#     assert res["num_submit"] == 0
#     assert res["num_accept"] == 0
#     assert res["data"] is None
#     assert res["data_version"] == 2
