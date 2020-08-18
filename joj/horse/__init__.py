from tenacity import retry, stop_after_attempt, wait_fixed, RetryError

from joj.horse.utils.fastapi import FastAPI
from joj.horse.utils.cache import test_cache
from joj.horse.utils.session import SessionMiddleware

app = FastAPI()

app.add_middleware(SessionMiddleware)

from uvicorn.config import logger


@app.on_event("startup")
async def startup_event():
    try:
        await test_cache()
    except RetryError as e:
        logger.error("Initialization failed, exiting.")
        logger.disabled = True
        exit(-1)


import joj.horse.apis
