from app.extensions import db


class ProviderService(db.Model):
    """Свързва Provider <-> Service. Наличието на ред тук = 'този служител
    предлага тази услуга'. price / duration_minutes са по избор — ако не са
    зададени, важат стойностите от Service (глобалната цена/времетраене).
    """

    __tablename__ = "provider_service"

    id = db.Column(db.Integer, primary_key=True)
    provider_id = db.Column(db.Integer, db.ForeignKey("provider.id"), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey("service.id"), nullable=False)

    price = db.Column(db.Numeric(10, 2), nullable=True)
    duration_minutes = db.Column(db.Integer, nullable=True)

    __table_args__ = (
        db.UniqueConstraint("provider_id", "service_id", name="uq_provider_service"),
    )

    @staticmethod
    def get(provider_id, service_id):
        return ProviderService.query.filter_by(
            provider_id=provider_id, service_id=service_id
        ).first()

    def effective_price(self):
        return self.price if self.price is not None else self.service.price

    def effective_duration(self):
        return (
            self.duration_minutes
            if self.duration_minutes is not None
            else self.service.duration_minutes
        )

    def to_dict(self):
        return {
            "service_id": self.service_id,
            "service_name": self.service.name,
            "price": float(self.effective_price()) if self.effective_price() is not None else None,
            "duration_minutes": self.effective_duration(),
            "price_overridden": self.price is not None,
            "duration_overridden": self.duration_minutes is not None,
        }