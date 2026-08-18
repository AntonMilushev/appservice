from app.extensions import db


class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True)
    password = db.Column(db.String(100))
    role = db.Column(db.String(20))  # ADMIN / PROVIDER
    provider_id = db.Column(db.Integer, db.ForeignKey("provider.id"), nullable=True)