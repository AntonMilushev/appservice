from app.extensions import db
from datetime import time

class Barber(db.Model):
    __tablename__ = "barber"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    working_days = db.Column(db.String, default="1,2,3,4,5")
    working_start = db.Column(db.Time, default=time(9, 0))
    working_end = db.Column(db.Time, default=time(18, 0))
    break_start = db.Column(db.Time, nullable=True)
    break_end = db.Column(db.Time, nullable=True) 
    shop_id = db.Column(db.Integer)

    bookings = db.relationship('Booking', backref='barber', lazy=True)