from app.extensions import db
from datetime import datetime
from app.utils.time_utils import sofia_now


class EmailLog(db.Model):
    __tablename__ = "email_log"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('booking.id', ondelete='SET NULL'), nullable=True)

    to_email = db.Column(db.String(150))
    status_type = db.Column(db.String(20))   # accepted / rejected / pending
    subject = db.Column(db.String(200))

    success = db.Column(db.Boolean, default=False)
    error = db.Column(db.String(255), nullable=True)

    created_at = db.Column(db.DateTime, default=sofia_now)