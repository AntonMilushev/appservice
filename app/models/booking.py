from app.extensions import db
from datetime import datetime
from app.utils.time_utils import sofia_now

class Booking(db.Model):
    __tablename__ = "booking"

    id = db.Column(db.Integer, primary_key=True)

    user_name = db.Column(db.String(100), nullable=False)
    user_phone = db.Column(db.String(20))
    user_email = db.Column(db.String(100))

    created_at = db.Column(
    db.DateTime,
    default=sofia_now,
    nullable=False
)


    confirmed_at = db.Column(
    db.DateTime,
    nullable=True
)


    cancelled_at = db.Column(
    db.DateTime,
    nullable=True
)


    reminder_sent = db.Column(db.Boolean, default=False, nullable=False)


    barber_id = db.Column(db.Integer, db.ForeignKey('barber.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)

    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default="PENDING")
    shop_id = db.Column(db.Integer)
    service = db.relationship('Service')