import asyncio

from tenacity import RetryError
from starlette.responses import RedirectResponse
from fastapi import FastAPI

from joj.horse.config import settings
from joj.horse.utils.cache import test_cache
from joj.horse.utils.version import get_version, get_git_version
from joj.horse.utils.db import get_db, ensure_indexes
from joj.horse.utils.url import generate_url

app = FastAPI(
    title=settings.app_name,
    version=get_version(),
    description="Git version: " + get_git_version(),
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1",
    redoc_url="/api/v1/redoc",
)

app.add_middleware(SessionMiddleware)

from uvicorn.config import logger


@app.on_event("startup")
async def startup_event():
    try:
        logger.info("Using %s." % asyncio.get_running_loop().__module__)
        await test_cache()
        get_db()
        await ensure_indexes()
    except RetryError as e:
        logger.error("Initialization failed, exiting.")
        logger.disabled = True
        exit(-1)


# we temporarily redirect "/" to "/api/v1" for debugging
@app.get("/")
async def redirect_to_docs():
    redirect_url = generate_url("/api/v1")
    return RedirectResponse(redirect_url)


import joj.horse.apis
