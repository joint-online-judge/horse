from uuid import UUID

from sqlalchemy.schema import Column, ForeignKey
from sqlmodel import Field, SQLModel
from sqlmodel.sql.sqltypes import GUID


class ProblemProblemSetLink(SQLModel, table=True):  # type: ignore[call-arg]
    __tablename__ = "problem_problem_set_links"

    problem_id: UUID = Field(
        sa_column=Column(
            GUID, ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True
        ),
    )
    problem_set_id: UUID = Field(
        sa_column=Column(
            GUID, ForeignKey("problem_sets.id", ondelete="CASCADE"), primary_key=True
        ),
    )
