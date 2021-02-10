import logging
import inspect
import os

from uvicorn.config import LOGGING_CONFIG
from uvicorn.logging import DefaultFormatter, TRACE_LOG_LEVEL
import click

import joj.horse


class PathTruncatingFormatter(DefaultFormatter):
    MODULE_DIR = os.path.dirname(inspect.getfile(joj.horse))
    level_name_colors = {
        TRACE_LOG_LEVEL: lambda level_name: click.style(str(level_name), fg="blue"),
        logging.DEBUG: lambda level_name: click.style(str(level_name), fg="cyan"),
        logging.INFO: lambda level_name: click.style(str(level_name), fg="green"),
        logging.WARNING: lambda level_name: click.style(str(level_name), fg="yellow"),
        logging.ERROR: lambda level_name: click.style(str(level_name), fg="red"),
        logging.CRITICAL: lambda level_name: click.style(
            str(level_name), fg="bright_red"
        ),
    }

    def color_level_name(self, level_name, level_no):
        def default(level_name):
            return str(level_name)

        func = self.level_name_colors.get(level_no, default)
        return func(level_name)

    def format(self, record):
        levelname = record.levelname[0]
        if self.use_colors:
            levelname = self.color_level_name(levelname, record.levelno)
            if "color_message" in record.__dict__:
                record.msg = record.__dict__["color_message"]
                record.__dict__["message"] = record.getMessage()
        record.__dict__["levelletterprefix"] = levelname
        if 'pathname' in record.__dict__ and 'lineno' in record.__dict__:
            relative_path = os.path.relpath(record.pathname, PathTruncatingFormatter.MODULE_DIR)
            if not relative_path.startswith('..'):
                record.pathname = '%s:%d' % (relative_path, record.lineno)
            else:
                record.pathname = '(uvicorn)'
        return super(PathTruncatingFormatter, self).format(record)


log_config = LOGGING_CONFIG

log_config["formatters"]["default"]["()"] = "joj.horse.utils.logger.PathTruncatingFormatter"

log_config["formatters"]["default"]["fmt"] = \
    '[%(levelletterprefix)s %(asctime)s %(pathname)s] %(message)s'
log_config["formatters"]["access"]["fmt"] = \
    '[%(levelletterprefix)s %(asctime)s %(client_addr)s] "%(request_line)s" %(status_code)s'

log_config["formatters"]["default"]["datefmt"] = '%Y-%m-%d %H:%M:%S'
log_config["formatters"]["access"]["datefmt"] = '%Y-%m-%d %H:%M:%S'
