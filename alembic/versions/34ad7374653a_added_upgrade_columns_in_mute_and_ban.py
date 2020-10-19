"""Added upgrade columns in mute and ban

Revision ID: 34ad7374653a
Revises:
Create Date: 2020-10-19 12:20:13.805900

"""
from alembic import op

# revision identifiers, used by Alembic.
from sqlalchemy import Boolean, Column

revision = "34ad7374653a"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("mute", Column("upgraded", Boolean, default=False))
    op.add_column("mute", Column("is_upgrade", Boolean, default=False))
    op.add_column("ban", Column("upgraded", Boolean, default=False))
    op.add_column("ban", Column("is_upgrade", Boolean, default=False))


def downgrade():
    op.drop_column("mute", "upgraded")
    op.drop_column("mute", "is_upgrade")
    op.drop_column("ban", "upgraded")
    op.drop_column("ban", "is_upgrade")
