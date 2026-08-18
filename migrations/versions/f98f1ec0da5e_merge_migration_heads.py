"""merge migration heads

Revision ID: f98f1ec0da5e
Revises: 8d0a955ac5aa, e51ce3ee94bb
Create Date: 2026-08-15 15:19:46.977597

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f98f1ec0da5e'
down_revision = ('8d0a955ac5aa', 'e51ce3ee94bb')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
