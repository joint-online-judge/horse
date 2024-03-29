"""add problem order

Revision ID: a418d86cb784
Revises: e789256f63f5
Create Date: 2021-11-17 21:51:08.443750

"""
import sqlalchemy as sa
import sqlmodel
import sqlmodel.sql.sqltypes
from alembic import op

# revision identifiers, used by Alembic.
revision = "a418d86cb784"
down_revision = "e789256f63f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("ix_domain_invitations_url", table_name="domain_invitations")
    op.create_index(
        op.f("ix_domain_invitations_url"), "domain_invitations", ["url"], unique=False
    )
    op.create_unique_constraint(None, "domain_invitations", ["domain_id", "url"])
    op.add_column(
        "problem_problem_set_links",
        sa.Column("position", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_index(
        op.f("ix_problem_problem_set_links_position"),
        "problem_problem_set_links",
        ["position"],
        unique=False,
    )
    op.create_unique_constraint(
        None, "problem_problem_set_links", ["problem_set_id", "position"]
    )
    op.drop_index("ix_problem_sets_url", table_name="problem_sets")
    op.create_index(op.f("ix_problem_sets_url"), "problem_sets", ["url"], unique=False)
    op.create_unique_constraint(None, "problem_sets", ["domain_id", "url"])
    op.drop_index("ix_problems_url", table_name="problems")
    op.create_index(op.f("ix_problems_url"), "problems", ["url"], unique=False)
    op.create_unique_constraint(None, "problems", ["domain_id", "url"])
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, "problems", type_="unique")
    op.drop_index(op.f("ix_problems_url"), table_name="problems")
    op.create_index("ix_problems_url", "problems", ["url"], unique=False)
    op.drop_constraint(None, "problem_sets", type_="unique")
    op.drop_index(op.f("ix_problem_sets_url"), table_name="problem_sets")
    op.create_index("ix_problem_sets_url", "problem_sets", ["url"], unique=False)
    op.drop_constraint(None, "problem_problem_set_links", type_="unique")
    op.drop_index(
        op.f("ix_problem_problem_set_links_position"),
        table_name="problem_problem_set_links",
    )
    op.drop_column("problem_problem_set_links", "position")
    op.drop_constraint(None, "domain_invitations", type_="unique")
    op.drop_index(op.f("ix_domain_invitations_url"), table_name="domain_invitations")
    op.create_index(
        "ix_domain_invitations_url", "domain_invitations", ["url"], unique=False
    )
    # ### end Alembic commands ###
