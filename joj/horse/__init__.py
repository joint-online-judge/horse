from tenacity import RetryError

from joj.horse.config import settings
from joj.horse.utils.fastapi import FastAPI
from joj.horse.utils.cache import test_cache
from joj.horse.utils.session import SessionMiddleware
from joj.horse.utils.version import get_version, get_git_version
from joj.horse.utils.db import init_collections, ensure_indexes

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
        await test_cache()
        init_collections()
        await ensure_indexes()
    except RetryError as e:
        logger.error("Initialization failed, exiting.")
        logger.disabled = True
        exit(-1)


import joj.horse.apis

