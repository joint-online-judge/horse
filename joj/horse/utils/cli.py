import asyncio
from functools import lru_cache, wraps
from typing import Any, Callable, List, Optional, Tuple, Type

import click
from click_option_group import optgroup
from pydantic import BaseModel

from joj.horse.config import AllSettings, Settings


def parse_settings_group(cls: Type[BaseModel]) -> Tuple[str, str]:
    docstring = cls.__doc__ or ""
    help_index = docstring.find("\n\n")
    if help_index < 0:
        name = docstring
        help_str = ""
    else:
        name = docstring[:help_index]
        help_str = docstring[help_index + 2 :]
    return name, help_str


def get_option_name(name: str, _type: type) -> str:
    name = name.replace("_", "-")
    if _type == bool:
        return f"--{name}/--no-{name}"
    return f"--{name}"


def get_option_help(description: Optional[str], default: Any) -> str:
    result = (description or "") + "\n"
    if default is not None:
        result += f"[default: {str(default)}]"
    return result


@lru_cache()
def get_global_options() -> List[Any]:
    global_options = [click.argument("args", nargs=-1)]
    for cls in AllSettings:
        name, help_str = parse_settings_group(cls)
        global_options.append(optgroup.group(name=name, help=help_str))
        for key, value in cls.__fields__.items():
            opt_name = get_option_name(key, value.type_)
            help_str = get_option_help(value.field_info.description, value.default)
            global_options.append(
                optgroup.option(
                    opt_name,
                    type=value.type_,
                    help=help_str,
                    default=None,
                )
            )
    return global_options


def add_options(options: List[Any]) -> Callable[..., Callable[..., Any]]:
    def _add_options(func: Any) -> Callable[..., Any]:
        for option in reversed(options):
            func = option(func)
        return func

    return _add_options


def cli_command_start(name: str = None) -> Any:
    def decorator(func: Any) -> Any:
        context_settings = dict(
            help_option_names=["-h", "--help"],
            max_content_width=88,
        )

        @click.command(name=name, context_settings=context_settings)
        @add_options(get_global_options())
        @wraps(func)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        return wrapped

    return decorator


cli_settings = {}


def cli_command_end() -> Any:
    def decorator(func: Any) -> Any:
        @wraps(func)
        def wrapped(args: Any, **kwargs: Any) -> Any:
            new_kwargs = {}
            for key, value in kwargs.items():
                if key in Settings.__fields__:
                    if value is not None:
                        cli_settings[key] = value
                else:
                    new_kwargs[key] = value
            return func(*args, **new_kwargs)

        return wrapped

    return decorator


def cli_command(name: str = None) -> Any:
    def decorator(func: Any) -> Any:
        @cli_command_start(name=name)
        @cli_command_end()
        @wraps(func)
        def wrapped(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        return wrapped

    return decorator


def cli_async(f: Any) -> Any:
    @wraps(f)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return asyncio.run(f(*args, **kwargs))

    return wrapper
