from datetime import datetime, timedelta
from app.models.booking import Booking
from app.services.sms_service import send_booking_sms
from app.services.email_service import send_booking_email
from app.utils.time_utils import sofia_now
from app.extensions import db
from app.models.barber_absence import BarberAbsence
from app.utils.time_utils import sofia_now


WORK_START = 9
WORK_END = 18
SLOT_DURATION = 30


def approve_booking(booking):
    booking.status = "CONFIRMED"
    booking.confirmed_at = sofia_now()
    booking.cancelled_at = None

    db.session.commit()

    send_booking_email(
        booking.user_email,
        "accepted",
        booking.user_name,
        booking.start_time,
        booking_id=booking.id
    )

    send_booking_sms(
        booking.user_phone,
        "accepted",
        booking.user_name,
        booking.start_time,
        booking_id=booking.id
    )

    print("✅ APPROVE FUNCTION CALLED")


def reject_booking(booking):
    booking.status = "CANCELLED"
    booking.cancelled_at = sofia_now()
    booking.confirmed_at = None

    db.session.commit()

    send_booking_email(
        booking.user_email,
        "rejected",
        booking.user_name,
        booking.start_time,
        booking_id=booking.id
    )

    send_booking_sms(
        booking.user_phone,
        "rejected",
        booking.user_name,
        booking.start_time,
        booking_id=booking.id
    )

    print("❌ REJECT FUNCTION CALLED")

def send_upcoming_reminders():

    now = sofia_now()
    window_start = now + timedelta(minutes=39)
    window_end = now + timedelta(minutes=41)

    bookings = Booking.query.filter(
        Booking.status == "CONFIRMED",
        Booking.reminder_sent == False,
        Booking.start_time >= window_start,
        Booking.start_time <= window_end
    ).all()

    for b in bookings:
        send_booking_sms(
            b.user_phone,
            "reminder",
            b.user_name,
            b.start_time,
            booking_id=b.id
        )
        b.reminder_sent = True

    if bookings:
        db.session.commit()
        print(f"🔔 Изпратени {len(bookings)} напомняния")

    return len(bookings)


def generate_available_slots(barber, service, date_obj):
    if not barber or not service:
        return []

    if barber.working_days:
        weekday = date_obj.isoweekday()
        working_days = [int(d) for d in barber.working_days.split(",")]
        if weekday not in working_days:
            return []

    if not barber.working_start or not barber.working_end:
        return []

    start_of_day = datetime.combine(date_obj, barber.working_start)
    end_of_day = datetime.combine(date_obj, barber.working_end)

    # 🏖 ОТСЪСТВИЯ
    absences = BarberAbsence.query.filter(
        BarberAbsence.barber_id == barber.id,
        BarberAbsence.start_date <= date_obj,
        BarberAbsence.end_date >= date_obj
    ).all()

    absence_windows = []
    for a in absences:
        is_single_day = a.start_date == a.end_date == date_obj
        if is_single_day and (a.unavailable_from or a.unavailable_to):
            win_start = datetime.combine(date_obj, a.unavailable_from or barber.working_start)
            win_end = datetime.combine(date_obj, a.unavailable_to or barber.working_end)
            absence_windows.append((win_start, win_end))
        else:
            return []  # цял ден е неработен

    duration = service.duration_minutes

    bookings = Booking.query.filter(
        Booking.barber_id == barber.id,
        Booking.status != "CANCELLED",
        Booking.start_time < end_of_day,
        Booking.end_time > start_of_day
    ).all()

    slots = []
    current = start_of_day
    now = sofia_now()

    while current + timedelta(minutes=duration) <= end_of_day:
        slot_end = current + timedelta(minutes=duration)

        if current < now:
            current += timedelta(minutes=SLOT_DURATION)
            continue

        overlap = any(current < b.end_time and slot_end > b.start_time for b in bookings)

        in_break = False
        if barber.break_start and barber.break_end:
            break_start = datetime.combine(date_obj, barber.break_start)
            break_end = datetime.combine(date_obj, barber.break_end)
            if current < break_end and slot_end > break_start:
                in_break = True

        in_absence = any(current < w_end and slot_end > w_start for w_start, w_end in absence_windows)

        if not overlap and not in_break and not in_absence:
            slots.append(current.strftime("%H:%M"))

        current += timedelta(minutes=SLOT_DURATION)

    return slots