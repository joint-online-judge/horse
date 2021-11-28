from functools import wraps
from typing import Any

from loguru import logger
from tenacity import retry
from tenacity.stop import stop_after_attempt
from tenacity.wait import wait_exponential


def retry_init(name: str) -> Any:
    def wrapper(f: Any) -> Any:
        @wraps(f)
        @retry(stop=stop_after_attempt(5), wait=wait_exponential(2))
        async def wrapped(*args: Any, **kwargs: Any) -> Any:
            attempt_number = wrapped.retry.statistics["attempt_number"]
            try:
                result = await f(*args, **kwargs)
                logger.info("{} initialized", name)
                return result
            except Exception as e:
                max_attempt_number = wrapped.retry.stop.max_attempt_number
                msg = "{}: initialization failed ({}/{})".format(
                    name, attempt_number, max_attempt_number
                )
                if attempt_number < max_attempt_number:
                    msg += ", trying again after {} second.".format(2 ** attempt_number)
                else:
                    msg += "."
                logger.exception(e)
                logger.warning(msg)
                raise e

        return wrapped

    return wrapper
