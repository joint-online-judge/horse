from fastapi import *
from fastapi import Request as FastApiRequest

from joj.horse.utils.session import Session


class Request(FastApiRequest):
    @property
    def session(self) -> Session:
        assert (
                "session" in self.scope
        ), "SessionMiddleware must be installed to access request.session"
        return self.scope["session"]


class Pagination:
    def __init__(self, skip: int = 0, limit: int = 0):
        self.skip = skip
        self.limit = limit

