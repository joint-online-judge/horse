from tenacity import retry, stop_after_attempt, wait_fixed, RetryError
from fastapi.logger import logger

from joj.horse.utils.fastapi import FastAPI
from joj.horse.utils.cache import test_cache
from joj.horse.utils.session import SessionMiddleware

app = FastAPI()

app.add_middleware(SessionMiddleware)


@app.on_event("startup")
async def startup_event():
    pass

    # @retry(stop=stop_after_attempt(2), wait=wait_fixed(1))
    # async def init():
    #     print(1)
    #     # test_cache()
    #
    # try:
    #     await init()
    # except RetryError as e:
    #     print(111)
    #     print(e)
    #     logger.exception(e)



import joj.horse.apis
