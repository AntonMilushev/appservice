"""add booking confirmation timestamps

Revision ID: 80babc5950d8
Revises: 2f4944df4968
"""

from alembic import op


revision = "80babc5950d8"
down_revision = "2f4944df4968"
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    op.drop_column("booking", "cancelled_at")
    op.drop_column("booking", "confirmed_at")
