from app import create_app
from app.extensions import db
from app.models import User
from werkzeug.security import generate_password_hash

app = create_app()

with app.app_context():

    db.create_all()

    # 🔑 Само admin акаунт — всичко останало (служители, услуги,
    # график, цени) се добавя после от админ панела.
    if User.query.filter_by(username="admin").first() is None:
        db.session.add(
            User(
                username="admin",
                password=generate_password_hash("123"),
                role="ADMIN"
            )
        )
        db.session.commit()
        print("✅ Admin акаунт създаден (username: admin / password: 123)")
    else:
        print("ℹ️ Admin акаунтът вече съществува")

print("✅ Seed completed")