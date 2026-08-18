from app.extensions import db
from app.utils.time_utils import sofia_now


class ProviderAbsence(db.Model):
    __tablename__ = "provider_absence"

    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey("provider.id"), nullable=False)

    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)

    # само за 1-дневно отсъствие: позволява половин ден / по-ранен край и т.н.
    unavailable_from = db.Column(db.Time, nullable=True)
    unavailable_to = db.Column(db.Time, nullable=True)

    reason = db.Column(db.String(100))   # Отпуск / Болничен / Почивен ден / Друго
    note = db.Column(db.String(255))

    created_at = db.Column(db.DateTime, default=sofia_now)

    provider = db.relationship("Provider", backref="absences")