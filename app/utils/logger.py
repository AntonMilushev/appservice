from app.models import Log
from app.extensions import db
from flask import session

def log_action(action, description, barber_id=None):
    log = Log(
        user_id=session.get('user_id'),
        barber_id=barber_id,
        action=action,
        description=description
    )

    db.session.add(log)
    db.session.commit()