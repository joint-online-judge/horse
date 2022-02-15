from typing import TYPE_CHECKING, List, Type
from uuid import UUID

from sqlalchemy import event
from sqlalchemy.schema import Column, ForeignKey, UniqueConstraint
from sqlmodel import Field, Relationship
from sqlmodel.sql.sqltypes import GUID

from joj.horse.models.base import DomainURLORMModel, url_pre_save
from joj.horse.models.link_tables import ProblemProblemSetLink
from joj.horse.schemas.problem import ProblemDetail, WithLatestRecordType
from joj.horse.services.db import db_session

if TYPE_CHECKING:
    from joj.horse.models import (
        Domain,
        ProblemConfig,
        ProblemGroup,
        ProblemSet,
        Record,
        User,
    )


class Problem(DomainURLORMModel, ProblemDetail, table=True):  # type: ignore[call-arg]
    __tablename__ = "problems"
    __table_args__ = (UniqueConstraint("domain_id", "url"),)

    domain_id: UUID = Field(
        sa_column=Column(
            GUID, ForeignKey("domains.id", ondelete="CASCADE"), nullable=False
        )
    )
    domain: "Domain" = Relationship(back_populates="problems")

    owner_id: UUID | None = Field(
        sa_column=Column(
            GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        )
    )
    owner: "User" | None = Relationship(back_populates="owned_problems")

    problem_group_id: UUID | None = Field(
        sa_column=Column(
            GUID, ForeignKey("problem_groups.id", ondelete="SET NULL"), nullable=True
        )
    )
    problem_group: "ProblemGroup" | None = Relationship(back_populates="problems")

    problem_sets: List["ProblemSet"] = Relationship(
        back_populates="problems",
        link_model=ProblemProblemSetLink,
        sa_relationship_kwargs={
            "viewonly": True,
        },
    )
    problem_problem_set_links: List[ProblemProblemSetLink] = Relationship(
        back_populates="problem",
    )

    records: List["Record"] = Relationship(back_populates="problem")
    problem_configs: List["ProblemConfig"] = Relationship(back_populates="problem")

    @classmethod
    async def get_problems_with_record_states(
        cls,
        result_cls: Type[WithLatestRecordType],
        problem_set_id: UUID | None,
        problems: List["Problem"],
        user_id: UUID,
    ) -> List[WithLatestRecordType]:
        from joj.horse import models

        problem_ids = [problem.id for problem in problems]
        records = await models.Record.get_user_latest_records(
            problem_set_id=problem_set_id, problem_ids=problem_ids, user_id=user_id
        )
        problems = [
            result_cls(**problems[i].dict(), latest_record=records[i])
            for i, record in enumerate(records)
        ]
        return problems

    async def get_latest_problem_config(self) -> "ProblemConfig" | None:
        from joj.horse import models

        statement = (
            models.ProblemConfig.sql_select()
            .where(models.ProblemConfig.problem_id == self.id)
            .order_by(models.ProblemConfig.created_at.desc())  # type: ignore
            .limit(1)
        )
        async with db_session() as session:
            results = await session.exec(statement)
            return results.one_or_none()


event.listen(Problem, "before_insert", url_pre_save)
event.listen(Problem, "before_update", url_pre_save)
