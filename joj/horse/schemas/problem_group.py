import typing
from typing import Callable, List

from pydantic.typing import AnyCallable

from joj.horse.schemas.base import (
    BaseODMSchema,
    ReferenceSchema,
    reference_schema_validator,
)

if typing.TYPE_CHECKING:
    from joj.horse.schemas.problem import Problem


class ProblemGroup(BaseODMSchema):
    pass
    # FIXME: finish this
    # problems: List[ReferenceSchema['Problem']] = []

    # _validate_problems: Callable[
    #     [AnyCallable], classmethod
    # ] = reference_schema_validator("problems", Problem, each_item=True)
