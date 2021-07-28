from joj.horse.config import settings


def generate_url(*args: str, protocol: str = "http") -> str:
    assert protocol in ["http", "ws"]
    path = "/".join(args)
    if path and path[0] != "/":
        path = "/" + path  # pragma: no cover
    prefix = settings.http_url_prefix if protocol == "http" else settings.ws_url_prefix
    return prefix + path
