from app import create_app
from app.services.cleanup_service import cleanup_old_bookings

app = create_app()

with app.app_context():
    cleanup_old_bookings()
