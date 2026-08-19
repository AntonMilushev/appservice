from app.models import Log
from app.extensions import db
from flask import session

def log_action(action, description, provider_id):
    log = Log(
        user_id=session.get('user_id'),
        provider_id=provider_id,
        action=action,
        description=description
    )

    db.session.add(log)
    db.session.commit()