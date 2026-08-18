"""add email_log table

Revision ID: ab9f06256f7b
Revises: af76e5622171
Create Date: 2026-08-14 20:34:09.305815

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "ab9f06256f7b"
down_revision = "af76e5622171"
branch_labels = None
depends_on = None


def upgrade():
    # ---------------------------------------------------------
    # Create new tables
    # ---------------------------------------------------------

    op.create_table(
        "barber",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("image", sa.String(length=200), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("working_days", sa.String(), nullable=True),
        sa.Column("working_start", sa.Time(), nullable=True),
        sa.Column("working_end", sa.Time(), nullable=True),
        sa.Column("break_start", sa.Time(), nullable=True),
        sa.Column("break_end", sa.Time(), nullable=True),
        sa.Column("shop_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("barber_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "push_subscriptions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("barber_id", sa.Integer(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("p256dh", sa.Text(), nullable=False),
        sa.Column("auth", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=True,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "service",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "barber_absence",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("barber_id", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("unavailable_from", sa.Time(), nullable=True),
        sa.Column("unavailable_to", sa.Time(), nullable=True),
        sa.Column("reason", sa.String(length=100), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["barber_id"],
            ["barber.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

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

    # ---------------------------------------------------------
    # Update booking table
    # ---------------------------------------------------------

    with op.batch_alter_table(
        "booking",
        schema=None,
        naming_convention={
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"
        },
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "user_name",
                sa.String(length=100),
                nullable=False,
            )
        )

        batch_op.add_column(
            sa.Column(
                "user_phone",
                sa.String(length=20),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "user_email",
                sa.String(length=100),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "reminder_sent",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )

        batch_op.add_column(
            sa.Column(
                "barber_id",
                sa.Integer(),
                nullable=False,
            )
        )

        batch_op.add_column(
            sa.Column(
                "service_id",
                sa.Integer(),
                nullable=False,
            )
        )

        batch_op.add_column(
            sa.Column(
                "start_time",
                sa.DateTime(),
                nullable=False,
            )
        )

        batch_op.add_column(
            sa.Column(
                "end_time",
                sa.DateTime(),
                nullable=False,
            )
        )

        batch_op.add_column(
            sa.Column(
                "status",
                sa.String(length=20),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "shop_id",
                sa.Integer(),
                nullable=True,
            )
        )

        # Old FK: booking.user_id -> user.id
        # The original constraint was unnamed.
        batch_op.drop_constraint(
            "fk_booking_user_id_user",
            type_="foreignkey",
        )

        batch_op.create_foreign_key(
            "fk_booking_barber_id_barber",
            "barber",
            ["barber_id"],
            ["id"],
        )

        batch_op.create_foreign_key(
            "fk_booking_service_id_service",
            "service",
            ["service_id"],
            ["id"],
        )

        batch_op.drop_column("barber_name")
        batch_op.drop_column("user_id")
        batch_op.drop_column("created_at")
        batch_op.drop_column("time")

    # ---------------------------------------------------------
    # Update user table
    # ---------------------------------------------------------

    with op.batch_alter_table("user", schema=None) as batch_op:

        batch_op.add_column(
            sa.Column(
                "password",
                sa.String(length=100),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "role",
                sa.String(length=20),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "shop_id",
                sa.Integer(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "barber_id",
                sa.Integer(),
                nullable=True,
            )
        )

        batch_op.alter_column(
            "username",
            existing_type=sa.VARCHAR(length=80),
            type_=sa.String(length=50),
            nullable=True,
        )

        batch_op.create_foreign_key(
            "fk_user_barber_id_barber",
            "barber",
            ["barber_id"],
            ["id"],
        )

        batch_op.drop_column("password_hash")
        batch_op.drop_column("is_admin")


def downgrade():
    # ---------------------------------------------------------
    # Revert user table
    # ---------------------------------------------------------

    with op.batch_alter_table("user", schema=None) as batch_op:

        batch_op.add_column(
            sa.Column(
                "is_admin",
                sa.BOOLEAN(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "password_hash",
                sa.VARCHAR(length=128),
                nullable=False,
            )
        )

        batch_op.drop_constraint(
            "fk_user_barber_id_barber",
            type_="foreignkey",
        )

        batch_op.alter_column(
            "username",
            existing_type=sa.String(length=50),
            type_=sa.VARCHAR(length=80),
            nullable=False,
        )

        batch_op.drop_column("barber_id")
        batch_op.drop_column("shop_id")
        batch_op.drop_column("role")
        batch_op.drop_column("password")

    # ---------------------------------------------------------
    # Revert booking table
    # ---------------------------------------------------------

    with op.batch_alter_table(
        "booking",
        schema=None,
        naming_convention={
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"
        },
    ) as batch_op:

        batch_op.add_column(
            sa.Column(
                "time",
                sa.DATETIME(),
                nullable=False,
            )
        )

        batch_op.add_column(
            sa.Column(
                "created_at",
                sa.DATETIME(),
                nullable=True,
            )
        )

        batch_op.add_column(
            sa.Column(
                "user_id",
                sa.INTEGER(),
                nullable=False,
            )
        )

        batch_op.add_column(
            sa.Column(
                "barber_name",
                sa.VARCHAR(length=50),
                nullable=False,
            )
        )

        batch_op.drop_constraint(
            "fk_booking_service_id_service",
            type_="foreignkey",
        )

        batch_op.drop_constraint(
            "fk_booking_barber_id_barber",
            type_="foreignkey",
        )

        batch_op.create_foreign_key(
            "fk_booking_user_id_user",
            "user",
            ["user_id"],
            ["id"],
        )

        batch_op.drop_column("shop_id")
        batch_op.drop_column("status")
        batch_op.drop_column("end_time")
        batch_op.drop_column("start_time")
        batch_op.drop_column("service_id")
        batch_op.drop_column("barber_id")
        batch_op.drop_column("reminder_sent")
        batch_op.drop_column("user_email")
        batch_op.drop_column("user_phone")
        batch_op.drop_column("user_name")

    # ---------------------------------------------------------
    # Drop new tables
    # ---------------------------------------------------------

    op.drop_table("sms_log")
    op.drop_table("email_log")
    op.drop_table("barber_absence")
    op.drop_table("service")
    op.drop_table("push_subscriptions")
    op.drop_table("log")
    op.drop_table("barber")