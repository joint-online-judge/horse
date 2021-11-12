from typing import TYPE_CHECKING

from joj.horse.schemas.base import BaseORMSchema, IDMixin, TimestampMixin

if TYPE_CHECKING:
    pass


class ProblemGroup(BaseORMSchema, IDMixin):
    pass


class ProblemGroupDetail(TimestampMixin, ProblemGroup):
    pass
