import functools
from enum import Enum

from sanic_restplus import Namespace as SanicNamespace
from webargs.fields import Field

from joj.horse import api
from joj.horse.utils.sanicparser import use_kwargs


class Locations(Enum):
    QUERY = "query"
    JSON = "json"
    FORM = "form"
    HEADERS = "headers"
    COOKIES = "cookies"
    FILES = "files"
    PATH = "path"

    def webargs(self):
        return self.value

    def doc(self):
        return _locations_to_doc[self]


_locations_to_doc = {
    Locations.QUERY: "query",
    Locations.JSON: "body",
    Locations.FORM: "formData",
    Locations.HEADERS: "header",
    Locations.COOKIES: "cookie",
    Locations.FILES: "",
    Locations.PATH: "",
}


class NameSpace(SanicNamespace):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def argument(self, name: str, field: Field, location: Locations = Locations.QUERY,
                 description: str = None, **kwargs):
        args = {name: field}

        def decorator(func):
            @functools.wraps(func)
            @use_kwargs(args, location=location.webargs())
            @self.param(name, description, _in=location.doc(), **kwargs)
            async def wrapped(*_args, **_kwargs):
                print(_args)
                print(_kwargs)
                return await func(*_args, **_kwargs)

            return wrapped

        return decorator


def create_namespace(*args, **kwargs):
    ns = NameSpace(*args, **kwargs)
    api.add_namespace(ns)
    return ns
