from joj.horse.config import settings


def get_prefix(protocol: str) -> str:
    if protocol == "http":
        if settings.https:
            protocol += "s"
    else:
        protocol = "ws"
    return f"{protocol}://{settings.domain}"


def generate_url(*args: str, protocol: str = "http") -> str:
    assert protocol in ["http", "ws"]
    path = "/".join(args)
    if path and path[0] != "/":
        path = "/" + path
    prefix = get_prefix(protocol)
    return prefix + path
