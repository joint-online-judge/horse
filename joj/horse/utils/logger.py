# https://gist.github.com/nkhitrov/a3e31cfcc1b19cba8e1b626276148c49
"""Configure handlers and formats for application loggers."""
import logging
import sys
from typing import Union, cast

# if you dont like imports of private modules
# you can move it to typing.py module
from loguru import logger
from uvicorn.logging import AccessFormatter


class InterceptHandler(logging.Handler):
    """
    Default handler from examples in loguru documentaion.
    See https://loguru.readthedocs.io/en/stable/overview.html#entirely-compatible-with-standard-logging
    """

    accessFormat = AccessFormatter(
        fmt='%(client_addr)s - "%(request_line)s" %(status_code)s'
    ).formatMessage

    def emit(self, record: logging.LogRecord) -> None:
        # Get corresponding Loguru level if it exists
        level: Union[int, str]
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back  # type: ignore
            depth += 1
        if record.name == "uvicorn.access":
            msg = InterceptHandler.accessFormat(record)
        else:
            msg = record.getMessage()
        logger.opt(depth=depth, exception=record.exc_info).log(level, msg)


def init_logging(test: bool = False) -> None:
    """
    Replaces logging handlers with a handler for using the custom handler.

    WARNING!
    if you call the init_logging in startup event function,
    then the first logs before the application start will be in the old format
    >>> app.add_event_handler("startup", init_logging)
    stdout:
    INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
    INFO:     Started reloader process [11528] using statreload
    INFO:     Started server process [6036]
    INFO:     Waiting for application startup.
    2020-07-25 02:19:21.357 | INFO     | uvicorn.lifespan.on:startup:34 - Application startup complete.
    """
    # disable handlers for specific uvicorn loggers
    # to redirect their output to the default uvicorn logger
    # works with uvicorn==0.11.6
    uvicorn_loggers = (
        logging.getLogger(name)
        for name in logging.root.manager.loggerDict
        if name.startswith("uvicorn.")
    )
    for uvicorn_logger in uvicorn_loggers:
        uvicorn_logger.handlers = []

    # change handler for default uvicorn logger
    logging.getLogger("uvicorn").handlers = [InterceptHandler()]
    logging.getLogger("uvicorn.access").handlers = [InterceptHandler()]
    logging.getLogger("sqlalchemy").handlers = [InterceptHandler()]

    # set logs output, level and format
    logger.remove()
    if not test:
        logger.add(sys.stderr, level="DEBUG", enqueue=True)
        logger.add(
            "uvicorn.log",
            filter=lambda record: cast(str, record["name"]).startswith("uvicorn"),
            enqueue=True,
        )
        logger.add(
            "joj.horse.log",
            filter=lambda record: cast(str, record["name"]).startswith("joj.horse"),
            enqueue=True,
        )
        logger.add(
            "sqlalchemy.log",
            filter=lambda record: cast(str, record["name"]).startswith("sqlalchemy"),
            enqueue=True,
        )
