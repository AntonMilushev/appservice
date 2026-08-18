from app.extensions import db
from datetime import datetime
from app.utils.time_utils import sofia_now


class SmsLog(db.Model):
    __tablename__ = "sms_log"

    id = db.Column(db.Integer, primary_key=True)

    booking_id = db.Column(
        db.Integer,
        db.ForeignKey('booking.id', ondelete='SET NULL'),
        nullable=True
    )

    phone = db.Column(db.String(20))

    # Статусът на бизнес операцията:
    # accepted / rejected / pending / reminder
    status_type = db.Column(db.String(20))

    message = db.Column(db.String(255))

    success = db.Column(db.Boolean, default=False)

    # ID на SMS-а в BulkGate
    provider_sms_id = db.Column(
        db.String(100),
        nullable=True
    )

    # Реалният статус от BulkGate:
    # accepted / sent / delivered / unavailable / not_delivered
    provider_status = db.Column(
        db.String(30),
        nullable=True
    )

    # Кога BulkGate е потвърдил доставката
    delivered_at = db.Column(
        db.DateTime,
        nullable=True
    )

    # Пълният response от BulkGate
    provider_response = db.Column(
        db.Text,
        nullable=True
    )

    error = db.Column(
        db.String(255),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        default=sofia_now
    )

    booking = db.relationship('Booking')