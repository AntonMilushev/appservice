"""add booking timestamps

Revision ID: 2f4944df4968
Revises: ab9f06256f7b
"""

from alembic import op
import sqlalchemy as sa


revision = '2f4944df4968'
down_revision = 'ab9f06256f7b'
branch_labels = None
depends_on = None


def upgrade():

    # 1. Добавяме created_at като nullable,
    # защото SQLite не позволява директно NOT NULL колона
    # върху таблица, която вече има записи.
    op.add_column(
        'booking',
        sa.Column(
            'created_at',
            sa.DateTime(),
            nullable=True
        )
    )

    # 2. Попълваме старите записи.
    op.execute("""
        UPDATE booking
        SET created_at = CURRENT_TIMESTAMP
        WHERE created_at IS NULL
    """)

    # 3. Правим created_at NOT NULL.
    with op.batch_alter_table('booking') as batch_op:
        batch_op.alter_column(
            'created_at',
            existing_type=sa.DateTime(),
            nullable=False
        )

    # 4. Добавяме timestamp за потвърждение.
    op.add_column(
        'booking',
        sa.Column(
            'confirmed_at',
            sa.DateTime(),
            nullable=True
        )
    )

    # 5. Добавяме timestamp за отказ.
    op.add_column(
        'booking',
        sa.Column(
            'cancelled_at',
            sa.DateTime(),
            nullable=True
        )
    )


def downgrade():

    with op.batch_alter_table('booking') as batch_op:
        batch_op.drop_column('cancelled_at')
        batch_op.drop_column('confirmed_at')
        batch_op.drop_column('created_at')