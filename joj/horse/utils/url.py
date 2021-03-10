from joj.horse.config import settings


def generate_url(*args: str) -> str:
    path = "/".join(args)
    if not path or path[0] != "/":
        path = "/" + path
    return settings.url_prefix + path
