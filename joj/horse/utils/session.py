import asyncio
import uuid
from functools import lru_cache

from starlette.datastructures import MutableHeaders
from starlette.requests import HTTPConnection
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from pydantic import ValidationError

from joj.horse.utils.fastapi import HTTPException, Request

from joj.horse.config import settings
from joj.horse.utils.cache import get_cache
from joj.horse.models.session import Session


@lru_cache()
def get_caches():
    mem_cache = get_cache("default")
    session_cache = get_cache("session")
    return mem_cache, session_cache


async def get_session(key: uuid.UUID) -> Session:
    mem_cache, session_cache = get_caches()
    # try to get session from memory
    data = await mem_cache.get(str(key))
    # if not found in memory, find from redis
    if data is None:
        data = await session_cache.get(str(key))
    return Session(**data)


def create_session() -> Session:
    return Session(key=uuid.uuid4())


async def set_session(session: Session) -> None:
    mem_cache, session_cache = get_caches()
    await mem_cache.set(str(session.key), session.dict(), ttl=3600)
    await session_cache.set(str(session.key), session.dict(), ttl=settings.session_ttl)


async def clear_session(key: uuid.UUID) -> None:
    mem_cache, session_cache = get_caches()
    await mem_cache.delete(str(key))
    await session_cache.delete(str(key))


async def with_session(request: Request) -> Session:
    if not request.session:
        raise HTTPException(status_code=400, detail="Invalid authentication credentials")
    return request.session


class SessionMiddleware:
    def __init__(
            self,
            app: ASGIApp,
            # secret_key: typing.Union[str, Secret],
            session_cookie: str = "session",
            # max_age: int = 14 * 24 * 60 * 60,  # 14 days, in seconds
            same_site: str = "lax",
            https_only: bool = False,
    ) -> None:
        self.app = app
        # self.signer = itsdangerous.TimestampSigner(str(secret_key))
        self.session_cookie = session_cookie
        # self.max_age = max_age
        self.security_flags = "httponly; samesite=" + same_site
        if https_only:  # Secure flag can be used with HTTPS only
            self.security_flags += "; secure"

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):  # pragma: no cover
            await self.app(scope, receive, send)
            return

        connection = HTTPConnection(scope)
        initial_session_was_empty = True

        if self.session_cookie in connection.cookies:
            key = connection.cookies[self.session_cookie]
            try:
                scope["session"] = await get_session(uuid.UUID(key))
            except (TypeError, ValidationError, asyncio.TimeoutError):
                scope["session"] = create_session()

            # data = connection.cookies[self.session_cookie].encode("utf-8")
            # try:
            #     data = self.signer.unsign(data, max_age=self.max_age)
            #     scope["session"] = json.loads(b64decode(data))
            #     initial_session_was_empty = False
            # except (BadTimeSignature, SignatureExpired):
            #     scope["session"] = {}
        else:
            scope["session"] = create_session()

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                if scope["session"]:
                    # We have session data to persist.
                    # data = b64encode(json.dumps(scope["session"]).encode("utf-8"))
                    # data = self.signer.sign(data)
                    headers = MutableHeaders(scope=message)
                    header_value = "%s=%s; path=/; Max-Age=%d; %s" % (
                        self.session_cookie,
                        scope["session"].key,
                        settings.session_ttl,
                        self.security_flags,
                    )
                    headers.append("Set-Cookie", header_value)
                elif not initial_session_was_empty:
                    # The session has been cleared.
                    headers = MutableHeaders(scope=message)
                    header_value = "%s=%s; %s" % (
                        self.session_cookie,
                        "null; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT;",
                        self.security_flags,
                    )
                    headers.append("Set-Cookie", header_value)
            await send(message)

        await self.app(scope, receive, send_wrapper)
