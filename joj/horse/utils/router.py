import functools
from inspect import Parameter, signature
from typing import Any, Callable, List, get_type_hints

from fastapi import APIRouter, Depends

from joj.horse.schemas import BaseModel
from joj.horse.schemas.permission import PermissionBase
from joj.horse.utils.auth import ensure_permission


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
            if "permissions" in kwargs:
                permissions = kwargs["permissions"]
                new_dependencies = Depends(ensure_permission(permissions))
                kwargs["dependencies"] = list(kwargs.get("dependencies", []))
                kwargs["dependencies"].append(new_dependencies)
                if permissions is []:
                    kwargs["dependencies"].extend(Depends(ensure_permission()))
                kwargs.pop("permissions", None)
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
