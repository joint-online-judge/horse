import inspect
import os
from typing import Any

from uvicorn.config import LOGGING_CONFIG
from uvicorn.logging import AccessFormatter, ColourizedFormatter, DefaultFormatter

import joj.horse


def colourize(record: Any, msg: str) -> str:
    def color_level(level_name: str, level_no: int) -> str:
        def default(level_name: str) -> str:
            return str(level_name)

        func = ColourizedFormatter.level_name_colors.get(level_no, default)
        return func(level_name)

    l, r = msg.index("["), msg.index("]")
    return msg[:l] + color_level(msg[l : r + 1], record.levelno) + msg[r + 1 :]


class PathTruncatingFormatter(DefaultFormatter):
    MODULE_DIR = os.path.dirname(inspect.getfile(joj.horse))

    def format(self, record: Any) -> str:
        if "pathname" in record.__dict__ and "lineno" in record.__dict__:
            try:
                relative_path = os.path.relpath(
                    record.pathname, PathTruncatingFormatter.MODULE_DIR
                )
            except ValueError:
                relative_path = ""
            if relative_path and not relative_path.startswith(".."):
                record.pathname = "%s:%d" % (relative_path, record.lineno)
            else:
                record.pathname = "(uvicorn)"
        msg = super(PathTruncatingFormatter, self).format(record)
        return colourize(record, msg) if self.use_colors else msg


class MyColourizedFormatter(AccessFormatter):
    def format(self, record: Any) -> str:
        msg = super(MyColourizedFormatter, self).format(record)
        return colourize(record, msg) if self.use_colors else msg


log_config = LOGGING_CONFIG

log_config["formatters"]["default"][
    "()"
] = "joj.horse.utils.logger.PathTruncatingFormatter"
log_config["formatters"]["access"][
    "()"
] = "joj.horse.utils.logger.MyColourizedFormatter"

log_config["formatters"]["default"][
    "fmt"
] = "[%(levelname)1.1s %(asctime)s %(pathname)s] %(message)s"
log_config["formatters"]["access"][
    "fmt"
] = '[%(levelname)1.1s %(asctime)s %(client_addr)s] "%(request_line)s" %(status_code)s'

log_config["formatters"]["default"]["datefmt"] = "%Y-%m-%d %H:%M:%S"
log_config["formatters"]["access"]["datefmt"] = "%Y-%m-%d %H:%M:%S"

log_config["handlers"]["default_file"] = {
    "formatter": "default",
    "class": "logging.handlers.RotatingFileHandler",
    "filename": "fastapi.default.log",
    "maxBytes": 10 * 1024 * 1024,
    "backupCount": 5,
}

log_config["handlers"]["access_file"] = {
    "formatter": "access",
    "class": "logging.handlers.RotatingFileHandler",
    "filename": "fastapi.access.log",
    "maxBytes": 10 * 1024 * 1024,
    "backupCount": 5,
}

log_config["loggers"]["uvicorn"]["handlers"] = ["default", "default_file"]
log_config["loggers"]["uvicorn.access"]["handlers"] = ["access", "access_file"]
