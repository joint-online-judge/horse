from typing import Dict

from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient

from joj.horse import schemas
from joj.horse.apis import domains, user
from joj.horse.models.user import User
from joj.horse.tests.utils.utils import get_base_url, random_lower_string

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
NEW_DOMAIN = {}


def test_create_domain(
    client: TestClient, test_user_token_headers: Dict[str, str], test_user: User
) -> None:
    global NEW_DOMAIN
    r = client.post(f"{base_domain_url}", json=data, headers=test_user_token_headers)
    assert r.status_code == 200
    res = r.json()
    NEW_DOMAIN = res
    assert res["id"]
    assert res["url"] == domain.url
    assert res["name"] == domain.name
    assert res["bulletin"] == domain.bulletin
    assert res["gravatar"] == domain.gravatar
    assert res["owner"] == str(test_user.id)


def test_list_user_domains(
    client: TestClient, test_user_token_headers: Dict[str, str], test_user: User
) -> None:
    r = client.get(f"{base_user_url}/domains", headers=test_user_token_headers)
    assert r.status_code == 200
    res = r.json()
    assert res[0]["domain"] == NEW_DOMAIN
    assert res[0]["user"] == str(test_user.id)


def test_list_domains(
    client: TestClient, test_user_token_headers: Dict[str, str], test_user: User
) -> None:
    r = client.get(f"{base_domain_url}", headers=test_user_token_headers)
    assert r.status_code == 200
    res = r.json()
    assert res[0] == NEW_DOMAIN


def test_get_domain(
    client: TestClient, test_user_token_headers: Dict[str, str], test_user: User
) -> None:
    r = client.get(f"{base_domain_url}/{domain.url}", headers=test_user_token_headers)
    assert r.status_code == 200
    res = r.json()
    assert NEW_DOMAIN["owner"] == res["owner"]["id"]
    res["owner"] = NEW_DOMAIN["owner"]
    assert res == NEW_DOMAIN


def test_update_domain(
    client: TestClient, test_user_token_headers: Dict[str, str], test_user: User
) -> None:
    r = client.patch(
        f"{base_domain_url}/{domain.url}",
        json=update_data,
        headers=test_user_token_headers,
    )
    assert r.status_code == 200
    res = r.json()
    assert res["id"]
    assert res["url"] == domain.url
    assert res["name"] == domain_edit.name
    assert res["bulletin"] == domain_edit.bulletin
    assert res["gravatar"] == domain_edit.gravatar
    assert res["owner"] == str(test_user.id)
