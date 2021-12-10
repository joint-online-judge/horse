from pathlib import Path
from typing import Any, List, Optional

import click
import rapidjson
import uvicorn
from fastapi import FastAPI

from joj.horse.config import get_settings
from joj.horse.utils.cli import cli_command


@click.group(invoke_without_command=True)
@click.help_option("--help", "-h")
@click.pass_context
def cli_group(ctx: Any) -> Any:
    if ctx.invoked_subcommand is None:
        ctx.invoke(serve)


@cli_command()
def serve() -> None:  # pragma: no cover
    settings = get_settings()
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
def openapi(output: Optional[str], version: str) -> None:
    from joj.horse.app import app

    sub_app_path = f"/api/v{version}"
    for route in app.routes:
        sub_app = route.app
        if isinstance(sub_app, FastAPI) and route.path == sub_app_path:
            openapi_json = rapidjson.dumps(sub_app.openapi(), indent=2)
            if output is None:
                print(openapi_json)
            else:
                with Path(output).open("w", encoding="utf-8") as f:
                    f.write(openapi_json)
            exit(0)
    exit(-1)


if __name__ == "__main__":
    cli_group.add_command(serve)
    cli_group.add_command(openapi)
    cli_group()
