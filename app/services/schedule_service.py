from datetime import datetime, date
from app.extensions import db
from app.models.barber_absence import BarberAbsence
from app.models.booking import Booking
from app.utils.time_utils import sofia_now


def _parse_time(value):
    if not value:
        return None
    return datetime.strptime(value, "%H:%M").time()


def _parse_date(value):
    return datetime.strptime(value, "%Y-%m-%d").date()


def get_schedule(barber):
    return {
        "working_days": barber.working_days or "",
        "working_start": barber.working_start.strftime("%H:%M") if barber.working_start else None,
        "working_end": barber.working_end.strftime("%H:%M") if barber.working_end else None,
        "break_start": barber.break_start.strftime("%H:%M") if barber.break_start else None,
        "break_end": barber.break_end.strftime("%H:%M") if barber.break_end else None,
    }


def update_schedule(barber, data):
    working_days = data.get("working_days")

    if working_days is not None:
        days = [d.strip() for d in working_days.split(",") if d.strip()]
        for d in days:
            if not d.isdigit() or not (1 <= int(d) <= 7):
                raise ValueError("Невалидни работни дни (използвай 1-7, разделени със запетая)")
        barber.working_days = ",".join(days)

    if data.get("working_start") is not None:
        barber.working_start = _parse_time(data.get("working_start"))

    if data.get("working_end") is not None:
        barber.working_end = _parse_time(data.get("working_end"))

    # почивка - позволяваме да се изчисти (изпратен "" -> None)
    if "break_start" in data:
        barber.break_start = _parse_time(data.get("break_start"))

    if "break_end" in data:
        barber.break_end = _parse_time(data.get("break_end"))

    if barber.working_start and barber.working_end and barber.working_start >= barber.working_end:
        raise ValueError("Началото на работния ден трябва да е преди края")

    db.session.commit()
    return get_schedule(barber)


def list_absences(barber_id, include_past=False):
    query = BarberAbsence.query.filter_by(barber_id=barber_id)

    if not include_past:
        query = query.filter(BarberAbsence.end_date >= date.today())

    absences = query.order_by(BarberAbsence.start_date).all()

    return [
        {
            "id": a.id,
            "start_date": a.start_date.isoformat(),
            "end_date": a.end_date.isoformat(),
            "unavailable_from": a.unavailable_from.strftime("%H:%M") if a.unavailable_from else None,
            "unavailable_to": a.unavailable_to.strftime("%H:%M") if a.unavailable_to else None,
            "reason": a.reason,
            "note": a.note,
        }
        for a in absences
    ]


def create_absence(barber_id, data):
    if not data.get("start_date"):
        raise ValueError("Липсва начална дата")

    start_date = _parse_date(data["start_date"])
    end_date = _parse_date(data["end_date"]) if data.get("end_date") else start_date

    if end_date < start_date:
        raise ValueError("Крайната дата е преди началната")

    unavailable_from = _parse_time(data.get("unavailable_from"))
    unavailable_to = _parse_time(data.get("unavailable_to"))

    if start_date != end_date and (unavailable_from or unavailable_to):
        raise ValueError("Частично отсъствие (по час) е позволено само за един ден")

    absence = BarberAbsence(
        barber_id=barber_id,
        start_date=start_date,
        end_date=end_date,
        unavailable_from=unavailable_from,
        unavailable_to=unavailable_to,
        reason=(data.get("reason") or "Отпуск").strip(),
        note=(data.get("note") or "").strip(),
    )

    db.session.add(absence)
    db.session.commit()

    conflicts = _get_conflicting_bookings(barber_id, absence)
    return absence, conflicts


def _get_conflicting_bookings(barber_id, absence):
    start_dt = datetime.combine(absence.start_date, absence.unavailable_from or datetime.min.time())
    end_dt = datetime.combine(absence.end_date, absence.unavailable_to or datetime.max.time())

    bookings = Booking.query.filter(
        Booking.barber_id == barber_id,
        Booking.status.in_(["PENDING", "CONFIRMED"]),
        Booking.start_time < end_dt,
        Booking.end_time > start_dt,
    ).all()

    return [
        {
            "id": b.id,
            "name": b.user_name,
            "phone": b.user_phone,
            "start_time": b.start_time.isoformat(),
            "status": b.status,
        }
        for b in bookings
    ]


def delete_absence(barber_id, absence_id):
    absence = BarberAbsence.query.get(absence_id)

    if not absence or absence.barber_id != barber_id:
        return False

    db.session.delete(absence)
    db.session.commit()
    return True