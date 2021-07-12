from typing import Any, Callable

from fastapi import FastAPI

from joj.horse import app
from joj.horse.apis import admin as admin
from joj.horse.apis import domains as domains
from joj.horse.apis import misc as misc
from joj.horse.apis import problem_groups as problem_groups
from joj.horse.apis import problem_sets as problem_sets
from joj.horse.apis import problems as problems
from joj.horse.apis import records as records
from joj.horse.apis import user as user
from joj.horse.apis import users as users
from joj.horse.apis.problems import submit_solution_to_problem, update_problem_config


def include_router(module: Any) -> None:
    app.include_router(
        module.router,
        prefix=module.router_prefix
        + ("/" + module.router_name if module.router_name else ""),
        tags=[module.router_tag],
    )


include_router(domains)
include_router(problem_sets)
include_router(problems)
include_router(records)
include_router(problem_groups)
include_router(user)
include_router(users)
include_router(misc)
include_router(admin)


def update_schema_name(
    app: FastAPI, function: Callable, name: str  # type: ignore
) -> None:
    """
    Updates the Pydantic schema name for a FastAPI function that takes
    in a fastapi.UploadFile = File(...) or bytes = File(...).

    This is a known issue that was reported on FastAPI#1442 in which
    the schema for file upload routes were auto-generated with no
    customization options. This renames the auto-generated schema to
    something more useful and clear.

    Args:
        app: The FastAPI application to modify.
        function: The function object to modify.
        name: The new name of the schema.
    """
    for route in app.routes:
        if route.endpoint is function:
            route.body_field.type_.__name__ = name
            break


update_schema_name(app, submit_solution_to_problem, "ProblemSolutionSubmit")
update_schema_name(app, update_problem_config, "ProblemConfigEdit")
