from fastapi.testclient import TestClient

from joj.horse.apis.misc import router_prefix


def test_version(client: TestClient) -> None:
    r = client.get(f"{router_prefix}/version")
    res = r.json()
    assert r.status_code == 200
    assert res["version"]
    assert res["git"]


def test_jwt(client: TestClient) -> None:
    r = client.get(
        f"{router_prefix}/jwt",
        cookies={
            "jwt": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiI2MDNlODA0ODc3YWIwNzk2MDliYTkyMTIiLCJpYXQiOjE2MTkwMjQwNzEsIm5iZiI6MTYxOTAyNDA3MSwianRpIjoiNmQ0ZjQ0NWQtODJhNi00YThhLTg4MjktOTQwODIyYTIxNDhlIiwiZXhwIjoxNjIwMjMzNjcxLCJ0eXBlIjoiYWNjZXNzIiwiZnJlc2giOmZhbHNlLCJuYW1lIjoiYm9taW5nemgiLCJzY29wZSI6InNqdHUiLCJjaGFubmVsIjoiamFjY291bnQifQ.1j1NdhgUXRTKUReXWWgVDG96_Ryp50R3znVTpCGT5GY"
        },
    )
    res = r.json()
    assert r.status_code == 200
    assert res["jwt"]
