"""problem set timestamps

Revision ID: ba45dc7837de
Revises: a418d86cb784
Create Date: 2021-11-18 04:17:36.227218

"""
import sqlalchemy as sa
import sqlmodel
import sqlmodel.sql.sqltypes
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "ba45dc7837de"
down_revision = "a418d86cb784"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "problem_sets", sa.Column("due_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "problem_sets", sa.Column("lock_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "problem_sets",
        sa.Column("unlock_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.drop_column("problem_sets", "due_time")
    op.drop_column("problem_sets", "available_time")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "problem_sets",
        sa.Column(
            "available_time",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.add_column(
        "problem_sets",
        sa.Column(
            "due_time",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.drop_column("problem_sets", "unlock_at")
    op.drop_column("problem_sets", "lock_at")
    op.drop_column("problem_sets", "due_at")
    # ### end Alembic commands ###
