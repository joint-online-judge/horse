import sqlalchemy.exc
from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi_jwt_auth.exceptions import AuthJWTException
from loguru import logger
from starlette.responses import JSONResponse

from joj.horse.schemas.base import StandardErrorResponse
from joj.horse.utils.errors import BizError, ErrorCode
from joj.horse.utils.logger import init_logging  # noqa: F401


def authjwt_exception_handler(request: Request, exc: AuthJWTException) -> JSONResponse:
    # noinspection PyUnresolvedReferences
    return JSONResponse(
        status_code=exc.status_code, content={"detail": exc.message}
    )  # pragma: no cover


def business_exception_response(exc: BizError) -> JSONResponse:
    return JSONResponse(
        jsonable_encoder(
            StandardErrorResponse(error_code=exc.error_code, error_msg=exc.error_msg)
        ),
        status_code=status.HTTP_200_OK,
    )


async def sqlalchemy_integrity_error_handler(
    request: Request, exc: sqlalchemy.exc.IntegrityError
) -> JSONResponse:
    return business_exception_response(BizError(ErrorCode.IntegrityError, str(exc)))


async def business_exception_handler(request: Request, exc: BizError) -> JSONResponse:
    return business_exception_response(exc)


async def general_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:  # pragma: no cover
    logger.exception(f"Unexpected Error: {exc.__class__.__name__}")
    return business_exception_response(
        BizError(ErrorCode.InternalServerError, str(exc))
    )


def register_exception_handlers(app: FastAPI) -> None:
    version = f"v{app.version}"
    logger.info("Register exception handlers: {}", version)
    app.add_exception_handler(AuthJWTException, authjwt_exception_handler)
    app.add_exception_handler(
        sqlalchemy.exc.IntegrityError, sqlalchemy_integrity_error_handler
    )
    app.add_exception_handler(BizError, business_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)
