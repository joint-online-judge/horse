import asyncio
from functools import lru_cache, wraps

import click

from joj.horse.config import get_settings


@lru_cache()
def get_global_options():
    global_options = [click.argument("args", nargs=-1)]
    _settings = get_settings()
    for key, value in _settings.__fields__.items():
        opt_name = "--" + key.replace("_", "-")
        global_options.append(
            click.option(opt_name, type=value.type_, is_flag=(value.type_ == bool))
        )
    return global_options


def add_options(options):
    def _add_options(func):
        for option in reversed(options):
            func = option(func)
        return func

    return _add_options


def cli_command_start(name: str = None):
    def decorator(func):
        @click.command(name=name)
        @add_options(get_global_options())
        @wraps(func)
        def wrapped(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapped

    return decorator


def cli_command_end():
    _settings = get_settings()

    def decorator(func):
        @wraps(func)
        def wrapped(args, **kwargs):
            new_kwargs = {}
            for key, value in kwargs.items():
                if key in _settings.__fields__:
                    if value:
                        _settings.__setattr__(key, value)
                else:
                    new_kwargs[key] = value
            # from joj.horse.utils.db import get_db
            # get_db()
            return func(*args, **new_kwargs)

        return wrapped

    return decorator


def cli_command(name: str = None):
    def decorator(func):
        @cli_command_start(name=name)
        @cli_command_end()
        @wraps(func)
        def wrapped(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapped

    return decorator


def cli_async(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))

    return wrapper
