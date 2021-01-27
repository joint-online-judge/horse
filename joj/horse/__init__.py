import asyncio

from fastapi import FastAPI
from starlette.responses import RedirectResponse
from tenacity import RetryError
from uvicorn.config import logger

from joj.horse.config import settings
from joj.horse.utils.cache import test_cache
from joj.horse.utils.db import ensure_indexes, get_db
from joj.horse.utils.url import generate_url
from joj.horse.utils.version import get_git_version, get_version

app = FastAPI(
    title=settings.app_name,
    version=get_version(),
    description="Git version: " + get_git_version(),
    openapi_url="/api/v1/openapi.json",
    docs_url="/api/v1",
    redoc_url="/api/v1/redoc",
)


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
