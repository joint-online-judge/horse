from typing import TYPE_CHECKING, Any, Callable

from fastapi import FastAPI
from pydantic.fields import ModelField

from joj.horse.apis import (
    admin as admin,
    auth as auth,
    domains as domains,
    misc as misc,
    problem_groups as problem_groups,
    problem_sets as problem_sets,
    problems as problems,
    records as records,
    user as user,
    users as users,
)
from joj.horse.apis.auth import login
from joj.horse.apis.problem_sets import submit_solution_to_problem_set
from joj.horse.apis.problems import submit_solution_to_problem, update_problem_config
from joj.horse.app import app


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
include_router(auth)
include_router(misc)
include_router(admin)


def _get_schema(_app: FastAPI, function: Callable[..., Any]) -> ModelField:
    for route in _app.routes:
        if route.endpoint is function:
            return route.body_field
    assert False


def update_schema_name(_app: FastAPI, function: Callable[..., Any], name: str) -> None:
    """
    Updates the Pydantic schema name for a FastAPI function that takes
    in a fastapi.UploadFile = File(...) or bytes = File(...).

    This is a known issue that was reported on FastAPI#1442 in which
    the schema for file upload routes were auto-generated with no
    customization options. This renames the auto-generated schema to
    something more useful and clear.

    Args:
        _app: The FastAPI application to modify.
        function: The function object to modify.
        name: The new name of the schema.
    """
    if not TYPE_CHECKING:
        schema = _get_schema(_app, function)
        schema.type_.__name__ = name


def copy_schema(
    _app: FastAPI, function_src: Callable[..., Any], function_dest: Callable[..., Any]
) -> None:
    if not TYPE_CHECKING:
        schema_src = _get_schema(_app, function_src)
        schema_dest = _get_schema(_app, function_dest)
        schema_dest.type_ = schema_src.type_


update_schema_name(app, submit_solution_to_problem, "ProblemSolutionSubmit")
copy_schema(app, submit_solution_to_problem, submit_solution_to_problem_set)
update_schema_name(app, update_problem_config, "ProblemConfigEdit")
update_schema_name(app, login, "OAuth2PasswordRequestForm")
