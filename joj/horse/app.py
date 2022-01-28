import asyncio

import rollbar
from fastapi import Depends, FastAPI, Request
from fastapi.responses import ORJSONResponse
from fastapi_versioning import VersionedFastAPI
from lakefs_client.exceptions import ApiException as LakeFSApiException
from loguru import logger
from pydantic_universal_settings import init_settings
from rollbar.contrib.fastapi import ReporterMiddleware as RollbarMiddleware
from starlette.responses import RedirectResponse
from starlette_context import plugins
from starlette_context.middleware import RawContextMiddleware
from tenacity import RetryError

import joj.horse.models  # noqa: F401
import joj.horse.utils.monkey_patch  # noqa: F401
from joj.horse.config import AllSettings
from joj.horse.schemas.cache import try_init_cache
from joj.horse.services.db import db_session_dependency, try_init_db
from joj.horse.services.lakefs import try_init_lakefs
from joj.horse.utils.exception_handlers import register_exception_handlers
from joj.horse.utils.logger import init_logging  # noqa: F401
from joj.horse.utils.router import simplify_operation_ids
from joj.horse.utils.url import get_base_url
from joj.horse.utils.version import get_git_version, get_version

settings = init_settings(AllSettings)
app = FastAPI(
    title=settings.app_name,
    version=get_version(),
    description=f"Git version: {get_git_version()}",
    dependencies=[Depends(db_session_dependency)],
    default_response_class=ORJSONResponse,
    swagger_ui_parameters={"docExpansion": "none"},
)
init_logging()

import joj.horse.apis  # noqa: F401

app = VersionedFastAPI(
    app,
    version_format="{major}",
    prefix_format="/api/v{major}",
)


# we temporarily redirect "/" and "/api" to "/api/v1" for debugging
@app.get("/api")
@app.get("/")
async def redirect_to_docs(request: Request) -> RedirectResponse:  # pragma: no cover
    base_url = get_base_url(request, prefix="api/v1")
    redirect_url = app.url_path_for("swagger_ui_html").make_absolute_url(base_url)

    logger.info(base_url)
    logger.info(redirect_url)

    return RedirectResponse(redirect_url + "?docExpansion=none")


@app.on_event("startup")
async def startup_event() -> None:  # pragma: no cover
    try:
        logger.info(f"Using {asyncio.get_running_loop().__module__}.")
        initialize_tasks = [
            try_init_db(),
            try_init_cache(),
        ]
        if settings.lakefs_host:
            initialize_tasks.append(try_init_lakefs())
        else:
            logger.warning("LakeFS not configured! All file features will be disabled.")
        await asyncio.gather(*initialize_tasks)

    except (RetryError, LakeFSApiException) as e:
        logger.error("Initialization failed, exiting.")
        logger.error(e)
        exit(-1)


# if settings.dsn:  # pragma: no cover
#     sentry_sdk.init(dsn=settings.dsn, traces_sample_rate=settings.traces_sample_rate)
#     app.add_middleware(SentryAsgiMiddleware)
#     logger.info("sentry activated")

app.add_middleware(
    RawContextMiddleware,
    plugins=(plugins.RequestIdPlugin(), plugins.CorrelationIdPlugin()),
)
if settings.rollbar_access_token and not settings.dsn:  # pragma: no cover
    rollbar.init(
        settings.rollbar_access_token,
        environment="production" if not settings.debug else "debug",
        handler="async",
    )
    app.add_middleware(RollbarMiddleware)
    logger.info("rollbar activated")

for route in app.routes:
    sub_app = route.app
    if isinstance(sub_app, FastAPI):
        register_exception_handlers(sub_app)
        simplify_operation_ids(sub_app)
