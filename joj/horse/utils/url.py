from joj.horse.config import settings


def generate_url(*args):
    path = "/".join(args)
    if not path or path[0] != "/":
        path = "/" + path
    return settings.url_prefix + path
