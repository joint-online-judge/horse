"""remove lakefs access key

Revision ID: e18766f796a7
Revises: 538579eca05b
Create Date: 2022-05-20 21:50:11.296567

"""
import sqlalchemy as sa
import sqlmodel
import sqlmodel.sql.sqltypes
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "e18766f796a7"
down_revision = "538579eca05b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index("ix_user_access_keys_created_at", table_name="user_access_keys")
    op.drop_index("ix_user_access_keys_updated_at", table_name="user_access_keys")
    op.drop_table("user_access_keys")
    op.drop_column("records", "lakefs_access_key_id")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "records",
        sa.Column(
            "lakefs_access_key_id", sa.VARCHAR(), autoincrement=False, nullable=True
        ),
    )
    op.create_table(
        "user_access_keys",
        sa.Column(
            "created_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("timezone('utc'::text, CURRENT_TIMESTAMP)"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            postgresql.TIMESTAMP(timezone=True),
            server_default=sa.text("timezone('utc'::text, CURRENT_TIMESTAMP)"),
            autoincrement=False,
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column("id", postgresql.UUID(), autoincrement=False, nullable=False),
        sa.Column("service", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column("access_key_id", sa.VARCHAR(), autoincrement=False, nullable=False),
        sa.Column(
            "secret_access_key", sa.VARCHAR(), autoincrement=False, nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name="user_access_keys_user_id_fkey",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="user_access_keys_pkey"),
        sa.UniqueConstraint(
            "service", "user_id", name="user_access_keys_service_user_id_key"
        ),
    )
    op.create_index(
        "ix_user_access_keys_updated_at",
        "user_access_keys",
        ["updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_user_access_keys_created_at",
        "user_access_keys",
        ["created_at"],
        unique=False,
    )
    # ### end Alembic commands ###
