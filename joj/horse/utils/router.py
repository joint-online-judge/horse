from typing import TYPE_CHECKING, Any, Callable, get_type_hints

from fastapi import APIRouter
from pydantic import BaseModel


class Detail(BaseModel):
    detail: str


class MyRouter(APIRouter):
    """
    Overrides the route decorator logic to use the annotated return type as the `response_model` if unspecified.
    """

    if not TYPE_CHECKING:  # pragma: no branch

        def add_api_route(
            self, path: str, endpoint: Callable[..., Any], **kwargs: Any
        ) -> None:
            if kwargs.get("response_model") is None:
                kwargs["response_model"] = get_type_hints(endpoint).get("return")
            kwargs["responses"] = {403: {"model": Detail}}
            return super().add_api_route(path, endpoint, **kwargs)
