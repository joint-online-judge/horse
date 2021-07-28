import asyncio
from typing import Any

import sentry_sdk
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi_jwt_auth.exceptions import AuthJWTException
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from starlette.responses import JSONResponse, RedirectResponse
from tenacity import RetryError
from tortoise import Tortoise, exceptions as tortoise_exceptions
from uvicorn.config import logger

from joj.horse.config import settings
from joj.horse.utils.db import try_init_db
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.lakefs import (
    LakeFSApiException,
    examine_lakefs_buckets,
    try_init_lakefs,
)
from joj.horse.utils.url import generate_url
from joj.horse.utils.version import get_git_version, get_version

app = FastAPI(
    title=settings.app_name,
    version=get_version(),
    description=f"Git version: {get_git_version()}",
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1",
    redoc_url="/api/v1/redoc",
)


@app.on_event("startup")
async def startup_event() -> None:
    try:
        logger.info("Using %s." % asyncio.get_running_loop().__module__)
        await try_init_db()

        if settings.lakefs_host:  # pragma: no cover
            try_init_lakefs()
            examine_lakefs_buckets()
        else:
            logger.warning("LakeFS not configured! All file features will be disabled.")

    except (RetryError, LakeFSApiException) as e:  # pragma: no cover
        logger.error("Initialization failed, exiting.")
        logger.error(e)
        logger.disabled = True
        exit(-1)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await Tortoise.close_connections()
    logger.info("Tortoise-ORM shutdown")


# we temporarily redirect "/" and "/api" to "/api/v1" for debugging
@app.get("/api")
@app.get("/")
async def redirect_to_docs() -> RedirectResponse:  # pragma: no cover
    redirect_url = generate_url("/api/v1?docExpansion=none")
    return RedirectResponse(redirect_url)


@app.exception_handler(AuthJWTException)
def authjwt_exception_handler(
    request: Request, exc: AuthJWTException
) -> JSONResponse:  # pragma: no cover
    # noinspection PyUnresolvedReferences
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


def business_exception_response(exc: BizError) -> JSONResponse:
    return JSONResponse(
        jsonable_encoder(
            {"error_code": exc.error_code, "error_msg": exc.error_msg, "data": {}}
        ),
        status_code=status.HTTP_200_OK,
    )


@app.exception_handler(tortoise_exceptions.IntegrityError)
async def tortoise_integrity_error_handler(
    request: Request, exc: tortoise_exceptions.IntegrityError
) -> JSONResponse:
    return business_exception_response(BizError(ErrorCode.IntegrityError, str(exc)))


@app.exception_handler(tortoise_exceptions.FieldError)
async def tortoise_field_error_handler(
    request: Request, exc: tortoise_exceptions.FieldError
) -> JSONResponse:  # pragma: no cover
    return business_exception_response(BizError(ErrorCode.UnknownFieldError, str(exc)))


@app.exception_handler(BizError)
async def business_exception_handler(request: Request, exc: BizError) -> JSONResponse:
    return business_exception_response(exc)


async def catch_exceptions_middleware(request: Request, call_next: Any) -> JSONResponse:
    try:
        return await call_next(request)
    except Exception as e:  # pragma: no cover
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


sentry_sdk.init(dsn=settings.dsn, traces_sample_rate=settings.traces_sample_rate)
app.add_middleware(SentryAsgiMiddleware)
app.middleware("http")(catch_exceptions_middleware)

import joj.horse.apis
