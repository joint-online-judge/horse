from typing import TYPE_CHECKING, List

from sqlmodel import Relationship

from joj.horse.models.base import BaseORMModel
from joj.horse.schemas.problem_group import ProblemGroupDetail

if TYPE_CHECKING:
    from joj.horse.models import Problem


class ProblemGroup(BaseORMModel, ProblemGroupDetail, table=True):  # type: ignore[call-arg]
    __tablename__ = "problem_groups"

    problems: List["Problem"] = Relationship(back_populates="problem_group")
