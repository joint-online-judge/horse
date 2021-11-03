import random
import string
from typing import Any, Dict, Optional, Union

from fastapi.encoders import jsonable_encoder
from fastapi_jwt_auth import AuthJWT
from httpx import AsyncClient, Response

from joj.horse import apis, models
from joj.horse.utils.auth import auth_jwt_encode_user
from joj.horse.utils.errors import ErrorCode


def random_lower_string(length: int = 32) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=length))


def random_student_id() -> str:
    return f"5{random.randint(0,99):02}370910{random.randint(0,999):03}"


def random_ip() -> str:
    return ".".join(map(str, (random.randint(0, 255) for _ in range(4))))


def generate_auth_headers(user: models.User) -> Dict[str, str]:
    access_token, _ = auth_jwt_encode_user(auth_jwt=AuthJWT(), user=user)
    return {"Authorization": f"Bearer {access_token}"}


def get_path_by_url_type(model: Any, url_type: str) -> str:
    if url_type == "url":
        return model.url
    elif url_type == "id" or url_type == "pk":
        return model.id
    assert False


async def do_api_request(
    client: AsyncClient,
    method: str,
    url: str,
    user: models.User,
    query: Optional[Dict[str, str]] = None,
    data: Optional[Dict[str, str]] = None,
) -> Response:
    headers = generate_auth_headers(user)
    response = await client.request(
        method=method,
        url=url,
        params=query,
        json=jsonable_encoder(data),
        headers=headers,
    )
    print(response.json())
    return response


async def create_test_user() -> models.User:
    user_create = models.UserCreate(
        username=random_lower_string(),
        email=random_lower_string() + "@sjtu.edu.cn",
        password=random_lower_string(),
    )
    user = await models.User.create(user_create, None, random_ip())
    assert user is not None
    return user


async def create_test_domain(
    client: AsyncClient, owner: models.User, data: Dict[str, str]
) -> Response:
    base_domain_url = get_base_url(apis.domains)
    headers = generate_auth_headers(owner)
    response = await client.post(
        f"{base_domain_url}", json=jsonable_encoder(data), headers=headers
    )
    return response


async def validate_test_domain(
    response: Response,
    owner: models.User,
    domain: Union[Dict[str, str], models.Domain],
) -> models.Domain:
    assert response.status_code == 200
    res = response.json()
    assert res["error_code"] == ErrorCode.Success
    res = res["data"]
    assert res["id"]

    if isinstance(domain, dict):
        data = domain
    elif isinstance(domain, models.Domain):
        data = domain.dict()
    else:
        assert False

    if "url" in data:
        assert res["url"] == data["url"]
    else:
        assert res["url"] == res["id"]
    assert res["name"] == data["name"]
    assert res["bulletin"] == data.get("bulletin", "")
    assert res["gravatar"] == data.get("gravatar", "")

    if isinstance(domain, dict):
        assert res["owner_id"] == str(owner.id)
    elif isinstance(domain, models.Domain):
        assert res["owner_id"] == str(data["owner_id"])

    if isinstance(domain, dict):
        domain = await models.Domain.get_or_none(id=res["id"])
    return domain


def get_base_url(module: Any) -> str:
    return module.router_prefix + (
        "/" + module.router_name if module.router_name else ""
    )
