import functools
from inspect import Parameter, signature
from typing import TYPE_CHECKING, Any, Callable, List, get_type_hints

from fastapi import APIRouter, Depends, FastAPI
from fastapi.routing import APIRoute
from loguru import logger
from pydantic.fields import ModelField

from joj.horse.schemas import BaseModel
from joj.horse.schemas.permission import PermissionBase


class Detail(BaseModel):
    detail: str


class MyRouter(APIRouter):
    """
    Overrides the route decorator logic to use the annotated return type as the `response_model` if unspecified.
    Parse the permissions in endpoints args and add them to the dependencies.
    """

    def _parse_permissions(func: Callable[..., Any]) -> Callable[..., Any]:
        sig = signature(func)
        parameters = [
            Parameter(
                name="permissions",
                kind=Parameter.POSITIONAL_ONLY,
                default=None,
                annotation=List[PermissionBase],
            )
        ]
        sig = sig.replace(parameters=parameters)
        func.__signature__ = sig
        func.__annotations__["permissions"] = List[PermissionBase]

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            from joj.horse.schemas.auth import ensure_permission

            permissions = kwargs.pop("permissions", None)
            if permissions:
                new_dependencies = Depends(ensure_permission(permissions))
                kwargs["dependencies"] = list(kwargs.get("dependencies", []))
                kwargs["dependencies"].append(new_dependencies)
            return func(*args, **kwargs)

        return wrapper

    get = _parse_permissions(APIRouter.get)
    put = _parse_permissions(APIRouter.put)
    post = _parse_permissions(APIRouter.post)
    delete = _parse_permissions(APIRouter.delete)
    options = _parse_permissions(APIRouter.options)
    head = _parse_permissions(APIRouter.head)
    patch = _parse_permissions(APIRouter.patch)
    trace = _parse_permissions(APIRouter.trace)

    def add_api_route(
        self, path: str, endpoint: Callable[..., Any], **kwargs: Any
    ) -> None:
        if kwargs.get("response_model") is None:
            kwargs["response_model"] = get_type_hints(endpoint).get("return")
        kwargs["responses"] = {403: {"model": Detail}}
        return super().add_api_route(path, endpoint, **kwargs)


def simplify_operation_ids(app: FastAPI) -> None:
    """
    Simplify operation IDs so that generated clients have simpler api function names
    """
    version = f"v{app.version}"
    logger.info("Simplify operation ids: {}", version)
    for route in app.routes:
        if isinstance(route, APIRoute):
            route.operation_id = f"{version}_{route.name}"


def _get_schema(_app: FastAPI, function: Callable[..., Any]) -> ModelField:
    """
    Get the Pydantic schema of a FastAPI function.
    """
    for route in _app.routes:
        if route.endpoint is function:  # type: ignore
            return route.body_field  # type: ignore
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
    _app: FastAPI, function_src: Callable[..., Any], *function_dest: Callable[..., Any]
) -> None:
    """
    Copy the Pydantic schema from a FastAPI function to some other functions.

    This is useful because if update_schema_name is called for two functions
    with the same schema, two schemas (same but not merged) will be generated
    and some openapi client generator will provide weird model names.

    Args:
        _app: The FastAPI application to modify.
        function_src: The function object to copy the schema from.
        function_dest: The function objects to copy the schema to.
    """

    if not TYPE_CHECKING:
        for func in function_dest:
            schema_src = _get_schema(_app, function_src)
            schema_dest = _get_schema(_app, func)
            schema_dest.type_ = schema_src.type_
