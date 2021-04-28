from typing import Dict

from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient

from joj.horse import schemas
from joj.horse.apis import domains, user
from joj.horse.models.user import User
from joj.horse.tests.utils.utils import get_base_url, random_lower_string

base_user_url = get_base_url(user)
base_domain_url = get_base_url(domains)


def test_create_user_domain(
    client: TestClient, test_user_token_headers: Dict[str, str], test_user: User
) -> None:
    domain = schemas.DomainCreate(
        url=random_lower_string(),
        name=random_lower_string(),
        bulletin=random_lower_string(),
        gravatar=random_lower_string(),
    )
    data = jsonable_encoder(domain)
    r = client.post(f"{base_domain_url}", json=data, headers=test_user_token_headers)
    assert r.status_code == 200
    res = r.json()
    new_domain = res
    assert res["id"]
    assert res["url"] == domain.url
    assert res["name"] == domain.name
    assert res["bulletin"] == domain.bulletin
    assert res["gravatar"] == domain.gravatar
    assert res["owner"] == str(test_user.id)
    r = client.get(f"{base_user_url}/domains", headers=test_user_token_headers)
    assert r.status_code == 200
    res = r.json()
    assert res[0]["domain"] == new_domain
    assert res[0]["user"] == str(test_user.id)
    r = client.get(f"{base_domain_url}", headers=test_user_token_headers)
    assert r.status_code == 200
    res = r.json()
    assert res[0] == new_domain
    r = client.get(f"{base_domain_url}/{domain.url}", headers=test_user_token_headers)
    assert r.status_code == 200
    res = r.json()
    assert new_domain["owner"] == res["owner"]["id"]
    res["owner"] = new_domain["owner"]
    assert res == new_domain
