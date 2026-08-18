"""sync production schema

Revision ID: 8d0a955ac5aa
Revises: 2e10aacb67d7
"""

from alembic import op
import sqlalchemy as sa


revision = "8d0a955ac5aa"
down_revision = "2e10aacb67d7"
branch_labels = None
depends_on = None


def upgrade():

    op.create_table(
        "email_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=True),
        sa.Column("to_email", sa.String(length=150), nullable=True),
        sa.Column("status_type", sa.String(length=20), nullable=True),
        sa.Column("subject", sa.String(length=200), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=True),
        sa.Column("error", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["booking.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "sms_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("booking_id", sa.Integer(), nullable=True),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("status_type", sa.String(length=20), nullable=True),
        sa.Column("message", sa.String(length=255), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=True),
        sa.Column("provider_sms_id", sa.String(length=100), nullable=True),
        sa.Column("provider_status", sa.String(length=30), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("provider_response", sa.Text(), nullable=True),
        sa.Column("error", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["booking_id"],
            ["booking.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():

    op.drop_table("sms_log")
    op.drop_table("email_log")
