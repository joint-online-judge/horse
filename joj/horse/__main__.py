from pathlib import Path
from typing import Any, List, Optional

import click
import orjson
import uvicorn
from fastapi import FastAPI
from pydantic_universal_settings import cli, init_settings

from joj.horse.config import AllSettings, UnionSettings


@click.group(invoke_without_command=True)
@click.help_option("--help", "-h")
@click.pass_context
def cli_group(ctx: click.Context) -> Any:
    if ctx.invoked_subcommand is None:
        ctx.invoke(serve)


@cli.command()
def serve() -> None:  # pragma: no cover
    settings: UnionSettings = init_settings(AllSettings)
    reload_dirs: Optional[List[str]] = None
    if settings.debug:
        reload_dirs = ["joj", ".venv/lib/python3.8/site-packages/joj"]
    uvicorn.run(
        "joj.horse.app:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        forwarded_allow_ips=settings.forwarded_allow_ips,
        reload_dirs=reload_dirs,
        workers=settings.workers,
    )


@click.command("openapi")
@click.option("-o", "--output", type=click.Path(), required=False, default=None)
@click.option("-v", "--version", type=str, default="1")
@click.option("--pretty", is_flag=True)
def openapi(output: Optional[str], version: str, pretty: bool) -> None:
    from joj.horse.app import app

    sub_app_path = f"/api/v{version}"
    for route in app.routes:
        sub_app = route.app  # type: ignore
        if isinstance(sub_app, FastAPI) and route.path == sub_app_path:  # type: ignore
            if pretty:
                option = orjson.OPT_INDENT_2
            else:
                option = 0
            openapi_json = orjson.dumps(sub_app.openapi(), option=option)
            if output is None:
                print(openapi_json.decode("utf-8"))
            else:
                with Path(output).open("wb") as f:
                    f.write(openapi_json)
            exit(0)
    exit(-1)


if __name__ == "__main__":
    cli_group.add_command(serve)
    cli_group.add_command(openapi)
    cli_group()
