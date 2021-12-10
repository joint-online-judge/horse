import functools
from inspect import Parameter, signature
from typing import Any, Callable, List, get_type_hints

from fastapi import APIRouter, Depends, FastAPI
from fastapi.routing import APIRoute
from loguru import logger

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
            from joj.horse.utils.auth import ensure_permission

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
