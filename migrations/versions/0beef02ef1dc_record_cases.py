"""record cases

Revision ID: 0beef02ef1dc
Revises: 461fe2b71f78
Create Date: 2022-01-14 21:43:43.739557

"""
import sqlalchemy as sa
import sqlmodel
import sqlmodel.sql.sqltypes
from alembic import op

# revision identifiers, used by Alembic.
revision = "0beef02ef1dc"
down_revision = "461fe2b71f78"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "records", sa.Column("cases", sa.JSON(), server_default="[]", nullable=False)
    )
    op.add_column(
        "records", sa.Column("domain_id", sqlmodel.sql.sqltypes.GUID(), nullable=False)
    )
    op.create_foreign_key(
        None, "records", "domains", ["domain_id"], ["id"], ondelete="CASCADE"
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, "records", type_="foreignkey")
    op.drop_column("records", "domain_id")
    op.drop_column("records", "cases")
    # ### end Alembic commands ###
