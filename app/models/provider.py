from app.extensions import db
from datetime import time


class Provider(db.Model):
    """Човек, който предлага услуги (бивш 'Barber').
    Генерично име, за да може да се преизползва за други типове бизнес
    (фризьори, масажисти, лекари, инструктори и т.н.) — фронтендът решава
    как да го нарече ('Барбър', 'Специалист', 'Треньор'...).
    """

    __tablename__ = "provider"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    image = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)

    working_days = db.Column(db.String, default="1,2,3,4,5")
    working_start = db.Column(db.Time, default=time(9, 0))
    working_end = db.Column(db.Time, default=time(18, 0))
    break_start = db.Column(db.Time, nullable=True)
    break_end = db.Column(db.Time, nullable=True)

    bookings = db.relationship("Booking", backref="provider", lazy=True)

    # ProviderService редове за този provider (кои услуги предлага + override цена/времетраене)
    service_links = db.relationship(
        "ProviderService", backref="provider", lazy=True, cascade="all, delete-orphan"
    )