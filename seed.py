from app import create_app
from app.extensions import db
from app.models import Barber, Service, User
from werkzeug.security import generate_password_hash
from datetime import time

app = create_app()

with app.app_context():

    db.create_all()   # ✅ ТОВА ЛИПСВАШЕ

    # 👨‍🦱 Barbers
    if Barber.query.count() == 0:
        db.session.add_all([
            Barber(
                name="Костадин",
                working_start=time(10, 0),
                working_end=time(19, 0),
                break_start=time(13, 0),
                break_end=time(14, 0),
                image="/static/images/Koce.jpg",
                working_days="2,3,4,5,6"
            ),
            Barber(
                name="Лозан",
                working_start=time(10, 0),
                working_end=time(19, 0),
                break_start=time(13, 0),
                break_end=time(14, 0),
                image="/static/images/Lozan.jpg",
                working_days="2,3,4,5,6"
            )
        ])

    # ✂️ Services
    if Service.query.count() == 0:
        db.session.add_all([
            Service(name="Подстригване", duration_minutes=30),
            Service(name="Брада", duration_minutes=30),
            Service(name="Подстригване + Брада", duration_minutes=60)
        ])

    # 👤 Users
    if User.query.count() == 0:
        db.session.add_all([
            User(username="koce", password=generate_password_hash("123"), role="BARBER", barber_id=1),
            User(username="lozan", password=generate_password_hash("123"), role="BARBER", barber_id=2),
            User(username="admin", password=generate_password_hash("123"), role="ADMIN"),
        ])

    db.session.commit()

print("✅ Seed completed")