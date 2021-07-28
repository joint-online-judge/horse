from typing import TYPE_CHECKING
from uuid import UUID

from tortoise import fields

from joj.horse.models.base import BaseORMModel
from joj.horse.models.problem import Problem


class ProblemConfig(BaseORMModel):
    class Meta:
        table = "problem_configs"

    problem: fields.OneToOneRelation[Problem] = fields.OneToOneField(
        "models.Problem",
        related_name="configs",
        on_delete=fields.CASCADE,
        index=True,
    )

    ref = fields.CharField(max_length=64)
    data = fields.JSONField()

    if TYPE_CHECKING:
        problem_id: UUID
