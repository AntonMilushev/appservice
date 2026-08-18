from datetime import datetime, timedelta
from app.models.booking import Booking
from app.extensions import db
from app.utils.time_utils import sofia_now

def cleanup_old_bookings():
    now = sofia_now()
    cutoff = now - timedelta(hours=24)

    # 🔒 safety: трие само минали + потвърдени
    old_bookings = Booking.query.filter(
        Booking.end_time < cutoff,
        Booking.end_time < now,  # двойна защита
        Booking.status == "CONFIRMED"
    ).all()

    print(f"🧹 Found {len(old_bookings)} old bookings")

    for b in old_bookings:
        print(f"Deleting booking ID={b.id}, time={b.end_time}")
        db.session.delete(b)

    db.session.commit()