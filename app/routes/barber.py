from flask import Blueprint, jsonify, request, session, render_template, redirect
from app.extensions import db
from app.models import Booking, Service, Barber
from app.utils.logger import log_action
from datetime import datetime, timedelta
from app.services.booking_service import approve_booking, reject_booking
from app.models.push_subscription import PushSubscription
from app.services.booking_service import generate_available_slots
from app.metrics import record_booking_created, record_booking_status
from app.services.schedule_service import (
    get_schedule, update_schedule, list_absences, create_absence, delete_absence
)
from app.utils.time_utils import sofia_now
from datetime import time as time_cls

barber_bp = Blueprint('barber', __name__)


# ======================================================
# 🖥️ BARBER PANEL
# ======================================================
@barber_bp.route('/barber')
def barber_page():
    if session.get('role') != 'BARBER':
        return redirect('/login')

    return render_template("barber.html")


# ======================================================
# 📅 BOOKINGS (само неговите)
# ======================================================
@barber_bp.route('/barber/bookings')
def barber_bookings():
    if session.get('role') != 'BARBER':
        return jsonify({"error": "Unauthorized"}), 401

    barber_id = session.get('barber_id')
    date = request.args.get('date')

    query = Booking.query.filter_by(barber_id=barber_id)

    # 📆 филтър по дата
    if date:
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d").date()
            query = query.filter(db.func.date(Booking.start_time) == date_obj)
        except:
            return jsonify({"error": "Invalid date"}), 400

    bookings = query.order_by(Booking.start_time).all()

    return jsonify([
        {
            "id": b.id,
            "name": b.user_name,
            "service": b.service.name if b.service else "N/A",
            "time": b.start_time.strftime("%H:%M"),
            "status": b.status
        }
        for b in bookings
    ])


# ======================================================
# ✔ APPROVE
# ======================================================
@barber_bp.route('/booking/<int:id>/approve', methods=['POST'])
def approve_booking_route(id):
    if session.get('role') != 'BARBER':
        return jsonify({"error": "Unauthorized"}), 401

    barber_id = session.get('barber_id')

    booking = Booking.query.get(id)

    if not booking:
        return jsonify({"error": "Няма запис"}), 404

    if booking.barber_id != barber_id:
        return jsonify({"error": "Forbidden"}), 403

    from app.services.booking_service import approve_booking
    approve_booking(booking)
    record_booking_status(booking, "confirmed")   # ✅ ЕДНА логика

    log_action("BARBER_APPROVE", f"Booking {id} approved", barber_id)

    return jsonify({"message": "Approved"})


# ======================================================
# ❌ REJECT
# ======================================================
@barber_bp.route('/booking/<int:id>/reject', methods=['POST'])
def reject_booking_route(id):
    if session.get('role') != 'BARBER':
        return jsonify({"error": "Unauthorized"}), 401

    barber_id = session.get('barber_id')

    booking = Booking.query.get(id)

    if not booking:
        return jsonify({"error": "Няма запис"}), 404

    if booking.barber_id != barber_id:
        return jsonify({"error": "Forbidden"}), 403

    # 🔥 използвай service слоя
    from app.services.booking_service import reject_booking
    reject_booking(booking)
    record_booking_status(booking, "cancelled")

    # 📜 LOG
    log_action("BARBER_REJECT", f"Booking {id} rejected", barber_id)

    return jsonify({"message": "Rejected"})


@barber_bp.route('/booking/<int:id>/delete', methods=['POST'])
def delete_booking(id):
    if session.get('role') != 'BARBER':
        return jsonify({"error": "Unauthorized"}), 401

    barber_id = session.get('barber_id')

    booking = Booking.query.get(id)

    if not booking:
        return jsonify({"error": "Няма запис"}), 404

    if booking.barber_id != barber_id:
        return jsonify({"error": "Forbidden"}), 403

    db.session.delete(booking)
    db.session.commit()

    return jsonify({"message": "Deleted"})

@barber_bp.route('/barber/notifications')
def barber_notifications():
    if session.get('role') != 'BARBER':
        return jsonify({"error": "Unauthorized"}), 401

    barber_id = session.get('barber_id')

    count = Booking.query.filter_by(
        barber_id=barber_id,
        status="PENDING"
    ).count()

    return jsonify({
        "pending_count": count
    })

@barber_bp.route('/barber/pending')
def barber_pending():
    if session.get('role') != 'BARBER':
        return jsonify({"error": "Unauthorized"}), 401

    barber_id = session.get('barber_id')

    bookings = Booking.query.filter_by(
        barber_id=barber_id,
        status="PENDING"
    ).order_by(Booking.start_time).all()

    return jsonify([
        {
            "id": b.id,
            "name": b.user_name,
            "phone": b.user_phone,
            "service": b.service.name if b.service else "",
            "datetime": b.start_time.isoformat() 
        }
        for b in bookings
    ])


@barber_bp.route('/barber/schedule')
def barber_schedule():
    if session.get('role') != 'BARBER':
        return jsonify({"error": "Unauthorized"}), 401

    barber_id = session.get('barber_id')
    date = request.args.get('date')

    barber = Barber.query.get(barber_id)

    query = Booking.query.filter_by(
        barber_id=barber_id,
        status="CONFIRMED"
    )

    if date:
        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d").date()
            query = query.filter(db.func.date(Booking.start_time) == date_obj)
        except:
            return jsonify({"error": "Invalid date"}), 400

    bookings = query.all()

    return jsonify({
        "bookings": [
            {
                "id": b.id,
                "name": b.user_name,
                "phone": b.user_phone,
                "service": b.service.name if b.service else "",
                "start": b.start_time.isoformat(),
                "end": b.end_time.isoformat()
            }
            for b in bookings
        ],
        "working_start": barber.working_start.strftime("%H:%M") if barber.working_start else "09:00",
        "working_end": barber.working_end.strftime("%H:%M") if barber.working_end else "19:00"
    })

# ======================================================
# 🚪 LOGOUT
# ======================================================
@barber_bp.route('/barber/logout')
def barber_logout():
    session.clear()
    return redirect('/login')

@barber_bp.route('/subscribe', methods=['POST'])
def subscribe():
    if session.get('role') != 'BARBER':
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    barber_id = session.get('barber_id')

    existing = PushSubscription.query.filter_by(
        endpoint=data['endpoint']
    ).first()

    if existing:
        return jsonify({"message": "Already subscribed"})

    sub = PushSubscription(
        barber_id=barber_id,
        endpoint=data['endpoint'],
        p256dh=data['keys']['p256dh'],
        auth=data['keys']['auth']
    )

    db.session.add(sub)
    db.session.commit()

    return jsonify({"message": "Subscribed"})

@barber_bp.route('/barber/available-slots')
def barber_available_slots():
    if session.get('role') != 'BARBER':
        return jsonify({"error": "Unauthorized"}), 401

    barber_id = session.get('barber_id')
    date = request.args.get('date')
    service_id = request.args.get('service_id')

    if not date or not service_id:
        return jsonify([])

    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        service_id = int(service_id)
    except:
        return jsonify([])

    barber = Barber.query.get(barber_id)
    service = Service.query.get(service_id)

    if not barber or not service:
        return jsonify([])

    slots = generate_available_slots(barber, service, date_obj)

    return jsonify(slots)


# ======================================================
# ➕ BARBER ADD BOOKING MANUALLY
# ======================================================
@barber_bp.route('/barber/add-booking', methods=['POST'])
def barber_add_booking():
    if session.get('role') != 'BARBER':
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}

    barber_id = session.get('barber_id')
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip().replace(" ", "")
    service_id = data.get('service_id')
    time_str = data.get('appointment_time')

    if not barber_id:
        return jsonify({"error": "Липсва barber session"}), 400

    if not name or not phone or not service_id or not time_str:
        return jsonify({"error": "Попълни всички полета"}), 400

    try:
        service_id = int(service_id)
        start_time = datetime.fromisoformat(time_str)
    except Exception:
        return jsonify({"error": "Невалидни данни"}), 400

    barber = Barber.query.get(barber_id)
    service = Service.query.get(service_id)

    if not barber:
        return jsonify({"error": "Невалиден бръснар"}), 400

    if not service:
        return jsonify({"error": "Невалидна услуга"}), 400

    # ✅ fallback, ако новият барбър няма настройки
    if not barber.working_days:
        barber.working_days = "1,2,3,4,5,6"

    if not barber.working_start:
        barber.working_start = time_cls(10, 0)

    if not barber.working_end:
        barber.working_end = time_cls(19, 0)

    db.session.commit()

    if start_time < sofia_now():
        return jsonify({"error": "Не можеш да добавиш минал час"}), 400

    slots = generate_available_slots(barber, service, start_time.date())

    if start_time.strftime("%H:%M") not in slots:
        return jsonify({"error": "Часът е зает или извън работното време"}), 400

    end_time = start_time + timedelta(minutes=service.duration_minutes)

    booking = Booking(
        user_name=name,
        user_phone=phone,
        user_email="",
        barber_id=barber_id,
        service_id=service_id,
        start_time=start_time,
        end_time=end_time,
        status="CONFIRMED",
        confirmed_at=sofia_now()
    )

    db.session.add(booking)
    db.session.commit()

    record_booking_created(booking)
    record_booking_status(booking, "confirmed")

    return jsonify({
        "message": "Часът е добавен",
        "id": booking.id
    }), 201


@barber_bp.route('/barber/settings', methods=['GET'])
def barber_settings():
    if session.get('role') != 'BARBER':
        return jsonify({"error": "Unauthorized"}), 401

    barber = Barber.query.get(session.get('barber_id'))
    if not barber:
        return jsonify({"error": "Няма такъв бръснар"}), 404

    return jsonify(get_schedule(barber))


@barber_bp.route('/barber/settings', methods=['PUT'])
def barber_update_settings():
    if session.get('role') != 'BARBER':
        return jsonify({"error": "Unauthorized"}), 401

    barber = Barber.query.get(session.get('barber_id'))
    if not barber:
        return jsonify({"error": "Няма такъв бръснар"}), 404

    try:
        result = update_schedule(barber, request.get_json(silent=True) or {})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    log_action("UPDATE_SCHEDULE", "Барбър обнови своя график", barber.id)
    return jsonify(result)


@barber_bp.route('/barber/absences', methods=['GET'])
def barber_get_absences():
    if session.get('role') != 'BARBER':
        return jsonify({"error": "Unauthorized"}), 401

    return jsonify(list_absences(session.get('barber_id')))


@barber_bp.route('/barber/absences', methods=['POST'])
def barber_create_absence():
    if session.get('role') != 'BARBER':
        return jsonify({"error": "Unauthorized"}), 401

    barber_id = session.get('barber_id')

    try:
        absence, conflicts = create_absence(barber_id, request.get_json(silent=True) or {})
    except (ValueError, TypeError) as e:
        return jsonify({"error": str(e) or "Невалидни данни"}), 400

    log_action("CREATE_ABSENCE", f"{absence.reason} {absence.start_date}-{absence.end_date}", barber_id)
    return jsonify({"message": "OK", "id": absence.id, "conflicts": conflicts}), 201


@barber_bp.route('/barber/absences/<int:id>', methods=['DELETE'])
def barber_delete_absence(id):
    if session.get('role') != 'BARBER':
        return jsonify({"error": "Unauthorized"}), 401

    if not delete_absence(session.get('barber_id'), id):
        return jsonify({"error": "Няма такъв запис"}), 404

    return jsonify({"message": "Deleted"})