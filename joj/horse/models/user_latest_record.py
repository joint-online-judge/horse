from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy.schema import Column, ForeignKey, UniqueConstraint
from sqlmodel import Field
from sqlmodel.sql.sqltypes import GUID

from joj.horse.models.base import BaseORMModel

if TYPE_CHECKING:
    pass


class UserLatestRecord(BaseORMModel, table=True):  # type: ignore[call-arg]
    __tablename__ = "user_latest_records"
    __table_args__ = (
        UniqueConstraint("user_id", "problem_id", "problem_set_id", "record_id"),
    )

    user_id: UUID = Field(
        sa_column=Column(
            GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
        ),
    )
    problem_id: UUID = Field(
        sa_column=Column(
            GUID, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False
        ),
    )
    problem_set_id: Optional[UUID] = Field(
        sa_column=Column(
            GUID, ForeignKey("problem_sets.id", ondelete="CASCADE"), nullable=True
        ),
    )
    record_id: UUID = Field(
        sa_column=Column(
            GUID, ForeignKey("records.id", ondelete="CASCADE"), nullable=False
        ),
    )
