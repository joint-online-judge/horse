import asyncio
from typing import Any, Dict

import sentry_sdk
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi_jwt_auth.exceptions import AuthJWTException
from marshmallow.exceptions import ValidationError as MValidationError
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from starlette.responses import JSONResponse, RedirectResponse
from tenacity import RetryError

# from pydantic.error_wrappers import ValidationError
from tortoise import Tortoise
from uvicorn.config import logger

from joj.horse.config import settings

# from joj.horse.utils.cache import test_cache
from joj.horse.utils.db import init_tortoise
from joj.horse.utils.errors import BizError, ErrorCode
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
        await init_tortoise()
    except RetryError:
        logger.error("Initialization failed, exiting.")
        logger.disabled = True
        exit(-1)


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await Tortoise.close_connections()
    logger.info("Tortoise-ORM shutdown")


# we temporarily redirect "/" and "/api" to "/api/v1" for debugging
@app.get("/api")
@app.get("/")
async def redirect_to_docs() -> RedirectResponse:
    redirect_url = generate_url("/api/v1?docExpansion=none")
    return RedirectResponse(redirect_url)


# @app.exception_handler(ValidationError)
# async def validation_exception_handler(
#     request: Request, exc: ValidationError
# ) -> JSONResponse:
#     return JSONResponse(
#         content=jsonable_encoder({"detail": exc.errors()}),
#         status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
#     )


@app.exception_handler(AuthJWTException)
def authjwt_exception_handler(request: Request, exc: AuthJWTException) -> JSONResponse:
    # noinspection PyUnresolvedReferences
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


def business_exception_response(exc: BizError) -> JSONResponse:
    return JSONResponse(
        jsonable_encoder(
            {"error_code": exc.error_code, "error_msg": exc.error_msg, "data": {}}
        ),
        status_code=status.HTTP_200_OK,
    )


@app.exception_handler(MValidationError)
async def marshmallow_validation_exception_handler(
    request: Request, exc: MValidationError
) -> JSONResponse:
    if (
        isinstance(exc.messages, Dict)
        and exc.messages.get("url") == "Field value must be unique."
    ):
        return business_exception_response(BizError(ErrorCode.UrlNotUniqueError))
    return JSONResponse(
        content=jsonable_encoder({"detail": exc.messages}),
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


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


sentry_sdk.init(dsn=settings.dsn, traces_sample_rate=settings.traces_sample_rate)
app.add_middleware(SentryAsgiMiddleware)
app.middleware("http")(catch_exceptions_middleware)

import joj.horse.apis
