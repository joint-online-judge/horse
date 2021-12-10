"""
Generate the openapi schema
"""

from pathlib import Path
from typing import Optional

import click
import rapidjson
from fastapi import FastAPI

from joj.horse.app import app


@click.command("openapi")
@click.option("-o", "--output", type=click.Path(), required=False, default=None)
@click.option("-v", "--version", type=str, default="1")
def main(output: Optional[str], version: str) -> None:
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
    main()  # pylint: disable=no-value-for-parameter
