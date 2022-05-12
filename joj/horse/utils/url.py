from fastapi import Request
from starlette.datastructures import URL, URLPath

from joj.horse.config import settings


def get_base_url(request: Request, prefix: str = "") -> URL:
    url = f"{request.url.scheme}://{request.url.netloc}/{settings.root_path}{prefix}"
    return URL(url)


def generate_url(request: Request, *args: str, protocol: str = "http") -> str:
    assert protocol in ["http", "ws"]
    path = "/".join(args)
    if path and path[0] != "/":
        path = "/" + path
    if not protocol:
        protocol = request.url.scheme
    return URLPath(path, protocol).make_absolute_url(get_base_url(request))
