import random
import string
from typing import Any, Dict

from fastapi.encoders import jsonable_encoder
from fastapi_jwt_auth import AuthJWT
from httpx import AsyncClient, Response

from joj.horse import apis, models, schemas
from joj.horse.utils.auth import auth_jwt_encode
from joj.horse.utils.errors import ErrorCode


def random_lower_string(length: int = 32) -> str:
    return "".join(random.choices(string.ascii_lowercase, k=length))


def random_bool() -> bool:
    return bool(random.randint(0, 1))


def random_student_id() -> str:
    return f"5{random.randint(0,99):02}370910{random.randint(0,999):03}"


def random_ip() -> str:
    return ".".join(map(str, (random.randint(0, 255) for _ in range(4))))


def generate_auth_headers(user: models.User) -> Dict[str, str]:
    access_jwt = auth_jwt_encode(auth_jwt=AuthJWT(), user=user, channel="jaccount")
    return {"Authorization": f"Bearer {access_jwt}"}


def data_to_mongo(data: Dict[str, str]) -> Dict[str, str]:
    if "id" in data:
        data["_id"] = data["id"]
        data.pop("id")
    return data


async def create_test_user() -> models.User:
    user = await models.User.login_by_jaccount(
        random_student_id(), random_lower_string(), random_lower_string(), random_ip()
    )
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


def validate_test_domain(
    response: Response, owner: models.User, data: Dict[str, str]
) -> models.Domain:
    assert response.status_code == 200
    res = response.json()
    assert res["error_code"] == ErrorCode.Success
    res = res["data"]
    assert res["id"]
    if "url" in data:
        assert res["url"] == data["url"]
    else:
        assert res["url"] == res["id"]
    assert res["name"] == data["name"]
    assert res["bulletin"] == data.get("bulletin", "")
    assert res["gravatar"] == data.get("gravatar", "")
    assert res["owner"] == str(owner.id)
    return models.Domain.build_from_mongo(data_to_mongo(res))


def get_base_url(module: Any) -> str:
    return module.router_prefix + (
        "/" + module.router_name if module.router_name else ""
    )
