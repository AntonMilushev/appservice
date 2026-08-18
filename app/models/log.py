from app.extensions import db
from datetime import datetime
from app.utils.time_utils import sofia_now

class Log(db.Model):
    __tablename__ = "log"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(db.Integer)
    barber_id = db.Column(db.Integer)

    action = db.Column(db.String(100))  # APPROVE, DELETE, CREATE etc.
    description = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=sofia_now)