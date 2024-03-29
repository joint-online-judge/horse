"""record lakefs_access_key_id field

Revision ID: b74e9831f731
Revises: bd01fa88bcd3
Create Date: 2022-05-07 19:55:33.112098

"""
import sqlalchemy as sa
import sqlmodel
import sqlmodel.sql.sqltypes
from alembic import op

# revision identifiers, used by Alembic.
revision = "b74e9831f731"
down_revision = "bd01fa88bcd3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "records",
        sa.Column(
            "lakefs_access_key_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True
        ),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("records", "lakefs_access_key_id")
    # ### end Alembic commands ###
