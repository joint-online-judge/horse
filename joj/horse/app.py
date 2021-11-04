import asyncio
from typing import Any

import sentry_sdk
import sqlalchemy.exc
from fastapi import Depends, FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi_jwt_auth.exceptions import AuthJWTException
from loguru import logger
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from starlette.responses import JSONResponse, RedirectResponse
from starlette_context import plugins
from starlette_context.middleware import RawContextMiddleware
from tenacity import RetryError

import joj.horse.models  # noqa: F401
from joj.horse.config import get_settings
from joj.horse.utils.db import db_session_dependency, try_init_db
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.lakefs import (
    LakeFSApiException,
    examine_lakefs_buckets,
    try_init_lakefs,
)
from joj.horse.utils.url import get_base_url
from joj.horse.utils.version import get_git_version, get_version

settings = get_settings()
app = FastAPI(
    title=settings.app_name,
    version=get_version(),
    description=f"Git version: {get_git_version()}",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1",
    redoc_url="/api/v1/redoc",
    dependencies=[Depends(db_session_dependency)],
)


@app.on_event("startup")
async def startup_event() -> None:  # pragma: no cover
    try:
        logger.info("Using %s." % asyncio.get_running_loop().__module__)
        await try_init_db()

        if settings.lakefs_host:
            try_init_lakefs()
            examine_lakefs_buckets()
        else:
            logger.warning("LakeFS not configured! All file features will be disabled.")

    except (RetryError, LakeFSApiException) as e:
        logger.error("Initialization failed, exiting.")
        logger.error(e)
        logger.disabled = True
        exit(-1)


# we temporarily redirect "/" and "/api" to "/api/v1" for debugging
@app.get("/api")
@app.get("/")
async def redirect_to_docs(request: Request) -> RedirectResponse:  # pragma: no cover
    base_url = get_base_url(request)
    redirect_url = app.url_path_for("swagger_ui_html").make_absolute_url(base_url)

    logger.info(base_url)
    logger.info(redirect_url)

    return RedirectResponse(redirect_url + "?docExpansion=none")


@app.exception_handler(AuthJWTException)
def authjwt_exception_handler(request: Request, exc: AuthJWTException) -> JSONResponse:
    # noinspection PyUnresolvedReferences
    return JSONResponse(
        status_code=exc.status_code, content={"detail": exc.message}
    )  # pragma: no cover


def business_exception_response(exc: BizError) -> JSONResponse:
    return JSONResponse(
        jsonable_encoder(
            {"error_code": exc.error_code, "error_msg": exc.error_msg, "data": {}}
        ),
        status_code=status.HTTP_200_OK,
    )


@app.exception_handler(sqlalchemy.exc.IntegrityError)
async def sqlalchemy_integrity_error_handler(
    request: Request, exc: sqlalchemy.exc.IntegrityError
) -> JSONResponse:
    return business_exception_response(BizError(ErrorCode.IntegrityError, str(exc)))


@app.exception_handler(BizError)
async def business_exception_handler(request: Request, exc: BizError) -> JSONResponse:
    return business_exception_response(exc)


async def catch_exceptions_middleware(request: Request, call_next: Any) -> JSONResponse:
    try:
        return await call_next(request)
    except Exception as e:
        logger.exception(f"Unexcepted Error: {e.__class__.__name__}")
        return JSONResponse(
            jsonable_encoder(
                {
                    "error_code": ErrorCode.InternalServerError,
                    "error_msg": e.__class__.__name__,
                    "data": {},
                }
            ),
            status_code=status.HTTP_200_OK,
        )


if settings.dsn:  # pragma: no cover
    sentry_sdk.init(dsn=settings.dsn, traces_sample_rate=settings.traces_sample_rate)
app.add_middleware(SentryAsgiMiddleware)
app.middleware("http")(catch_exceptions_middleware)
app.add_middleware(
    RawContextMiddleware,
    plugins=(plugins.RequestIdPlugin(), plugins.CorrelationIdPlugin()),
)


import joj.horse.apis  # noqa: F401
