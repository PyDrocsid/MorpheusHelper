"""Added aoc solutions column

Revision ID: 29437a178c47
Revises: 34ad7374653a
Create Date: 2020-12-12 16:48:15.828968

"""
from alembic import op

# revision identifiers, used by Alembic.
from sqlalchemy import Column, Text

revision = "29437a178c47"
down_revision = "34ad7374653a"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("aoc_link", Column("solutions", Text(collation="utf8mb4_bin"), nullable=True))


def downgrade():
    op.drop_column("aoc_link", "solutions")
