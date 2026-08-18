from app.extensions import db


class Service(db.Model):
    """Каталожна услуга на бизнеса (напр. 'Подстригване', 'Масаж 60 мин').

    duration_minutes / price тук са ПОДРАЗБИРАЩИ СЕ стойности.
    Конкретен Provider може да ги override-не през ProviderService.
    """

    __tablename__ = "service"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    provider_links = db.relationship(
        "ProviderService", backref="service", lazy=True, cascade="all, delete-orphan"
    )