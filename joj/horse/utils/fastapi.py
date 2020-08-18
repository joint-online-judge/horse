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
