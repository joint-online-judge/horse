from typing import Any, Dict, Optional, Tuple, Union
from uuid import UUID

import jwt
import pytest
from fastapi.encoders import jsonable_encoder
from httpx import AsyncClient, Response
from pydantic import BaseModel
from pytest_lazyfixture import lazy_fixture

from joj.horse import apis, models, schemas
from joj.horse.config import settings
from joj.horse.utils.errors import ErrorCode

# def random_lower_string(length: int = 32) -> str:
#     return "".join(random.choices(string.ascii_lowercase, k=length))


# def random_ip() -> str:
#     return ".".join(map(str, (random.randint(0, 255) for _ in range(4))))

GLOBAL_DOMAIN_COUNT = 3
GLOBAL_PROBLEM_SET_COUNT = 2


user_access_tokens: Dict[UUID, str] = {}
user_refresh_tokens: Dict[UUID, str] = {}


def validate_response(
    response: Response, error_code: ErrorCode = ErrorCode.Success
) -> Dict[str, Any]:
    assert response.status_code == 200
    res = response.json()
    assert res["errorCode"] == error_code
    if error_code == ErrorCode.Success:
        assert res["data"]
    return res["data"]


def to_dict(data: Union[Dict[Any, Any], BaseModel]) -> Dict[Any, Any]:
    if isinstance(data, dict):
        return data
    elif isinstance(data, models.Domain):
        return data.dict(by_alias=True)
    else:
        assert False


def validate_url(res: Dict[Any, Any], data: Dict[Any, Any]) -> None:
    if "url" in data:
        assert res["url"] == data["url"]
    else:
        assert res["url"] == res["id"]


def validate_domain(
    res: Dict[Any, Any], data: Dict[Any, Any], domain: models.Domain, in_data: bool
) -> None:
    assert res["domainId"] == str(domain.id)
    if in_data:
        assert res["domainId"] == str(data["domainId"])


def validate_owner(
    res: Dict[Any, Any], data: Dict[Any, Any], owner: models.User, in_data: bool
) -> None:
    assert res["ownerId"] == str(owner.id)
    if in_data:
        assert res["ownerId"] == str(data["ownerId"])


def generate_auth_headers(user: models.User) -> Dict[str, str]:
    # access_token, _ = auth_jwt_encode_user(auth_jwt=AuthJWT(), user=user)
    access_token = user_access_tokens[user.id]
    return {"Authorization": f"Bearer {access_token}"}


def get_path_by_url_type(model: Any, url_type: str) -> str:
    if url_type == "url":
        return model.url
    if url_type == "id" or url_type == "pk":
        return model.id
    assert False


async def do_api_request(
    client: AsyncClient,
    method: str,
    url: str,
    user: models.User,
    query: Optional[Dict[str, str]] = None,
    data: Optional[Dict[str, str]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Response:
    if headers is None:
        headers = generate_auth_headers(user)
    response = await client.request(
        method=method,
        url=url,
        params=query,
        json=jsonable_encoder(data),
        headers=headers,
    )
    return response


async def create_test_user(
    client: AsyncClient, username: str, password: Optional[str] = None
) -> Response:
    if password is None:
        password = username
    user_create = schemas.UserCreate(
        username=username,
        email=username + "@sjtu.edu.cn",
        password=password,
    )
    base_auth_url = get_base_url(apis.auth)
    response = await client.post(
        f"{base_auth_url}/register",
        json=jsonable_encoder(user_create.dict()),
        params={"responseType": "json", "cookie": False},
    )
    return response


async def login_test_user(
    client: AsyncClient, username: str, password: Optional[str] = None
) -> Response:
    if password is None:
        password = username
    base_auth_url = get_base_url(apis.auth)
    response = await client.post(
        f"{base_auth_url}/login",
        data={
            "username": username,
            "password": password,
        },
        params={"responseType": "json", "cookie": False},
    )
    return response


async def validate_test_user(
    response: Response,
    username: str,
) -> Tuple[models.User, str, str]:
    res = validate_response(response)
    assert res["accessToken"]
    assert res["refreshToken"]
    payload = jwt.decode(
        res["accessToken"],
        key=settings.jwt_secret,
        verify=False,
        algorithms=[settings.jwt_algorithm],
    )
    assert payload["username"] == username
    assert payload["sub"]
    user = await models.User.get_or_none(id=payload["sub"])
    assert user
    return user, res["accessToken"], res["refreshToken"]


async def create_test_domain(
    client: AsyncClient, owner: models.User, data: Dict[str, Any]
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
    res = validate_response(response)
    assert res["id"]
    data = to_dict(domain)
    validate_url(res, data)
    validate_owner(res, data, owner, isinstance(domain, models.Domain))
    assert res["name"] == data["name"]
    assert res["bulletin"] == data.get("bulletin", "")
    assert res["gravatar"] == data.get("gravatar", "")
    if isinstance(domain, dict):
        domain = await models.Domain.get_or_none(id=res["id"])
    return domain


async def create_test_problem_set(
    client: AsyncClient, domain: models.Domain, owner: models.User, data: Dict[str, str]
) -> Response:
    base_problem_set_url = get_base_url(apis.problem_sets, domain=domain.id)
    headers = generate_auth_headers(owner)
    response = await client.post(
        f"{base_problem_set_url}", json=jsonable_encoder(data), headers=headers
    )
    return response


async def validate_test_problem_set(
    response: Response,
    domain: models.Domain,
    owner: models.User,
    problem_set: Union[Dict[str, str], models.ProblemSet],
) -> models.ProblemSet:
    res = validate_response(response)
    assert res["id"]
    data = to_dict(problem_set)
    validate_url(res, data)
    validate_domain(res, data, domain, isinstance(problem_set, models.ProblemSet))
    validate_owner(res, data, owner, isinstance(problem_set, models.ProblemSet))
    assert res["title"] == data["title"]
    assert res["content"] == data.get("content", "")
    assert res["hidden"] == data.get("hidden", False)
    assert res["scoreboardHidden"] == data.get("scoreboardHidden", False)
    if isinstance(problem_set, dict):
        problem_set = await models.ProblemSet.get_or_none(id=res["id"])
    return problem_set


def get_base_url(module: Any, **kwargs: Any) -> str:
    s = module.router_prefix + ("/" + module.router_name if module.router_name else "")
    return s.format(**kwargs)


def parametrize_global_domains(func: Any) -> Any:
    fixtures = [lazy_fixture(f"global_domain_{i}") for i in range(GLOBAL_DOMAIN_COUNT)]
    return pytest.mark.parametrize("domain", fixtures)(func)


def parametrize_global_problem_sets(func: Any) -> Any:
    fixtures = [
        lazy_fixture(f"global_problem_set_{i}") for i in range(GLOBAL_PROBLEM_SET_COUNT)
    ]
    return pytest.mark.parametrize("problem_set", fixtures)(func)
