from functools import lru_cache, wraps
import asyncio

import click
from pydantic import BaseSettings


class Settings(BaseSettings):
    """
    Define the settings (config) of the website.

    The selected value is determined as follows (in descending order of priority):
    1. The command line arguments, e.g., '--db-host' is mapped to 'db-host'
    2. Environment variables, e.g., '$DB_HOST' is mapped to 'db-host'
    3. Variables loaded from a dotenv (.env) file
    4. The default field values for the Settings model
    """
    app_name: str = "JOJ Horse"
    host: str = "127.0.0.1"
    port: int = 34765
    url_prefix: str = "http://%s:%d" % (host, port)

    session_ttl: int = 14 * 24 * 60 * 60  # 14 days, in seconds

    # mongodb config
    db_host: str = "localhost"
    db_port: int = 27017
    db_name: str = "horse-production"

    # redis config
    redis_host: str = "localhost"
    redis_port: int = 6379

    # oauth config
    oauth_jaccount: bool = False
    oauth_jaccount_id: str = ''
    oauth_jaccount_secret: str = ''

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'


@lru_cache()
def get_settings():
    return Settings()


@lru_cache()
def get_global_options():
    global_options = [
        click.argument('args', nargs=-1)
    ]
    _settings = get_settings()
    for key, value in _settings.__fields__.items():
        opt_name = "--" + key.replace('_', '-')
        global_options.append(click.option(opt_name, type=value.type_, is_flag=(value.type_ == bool)))
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


settings = get_settings()
