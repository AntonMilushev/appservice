from app import create_app
from app.extensions import db

app = create_app()

with app.app_context():
    db.session.execute(db.text("""
        ALTER TABLE booking
        ADD COLUMN reminder_sent BOOLEAN NOT NULL DEFAULT 0
    """))
    db.session.commit()

print("✅ reminder_sent added")