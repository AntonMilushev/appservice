from flask import Blueprint, jsonify, request, session, render_template, redirect
from app.extensions import db
from app.models import Booking, Service, Provider
from app.utils.logger import log_action
from datetime import datetime, timedelta
from app.services.booking_service import (
    approve_booking, reject_booking, generate_available_slots,
    provider_offers_service, get_effective_duration
)
from app.models.push_subscription import PushSubscription
from app.metrics import record_booking_created, record_booking_status
from app.services.schedule_service import (
    get_schedule, update_schedule, list_absences, create_absence, delete_absence
)
from app.utils.time_utils import sofia_now
from datetime import time as time_cls

provider_bp = Blueprint('provider', __name__)


# ======================================================
# 🖥️ PROVIDER PANEL
# ======================================================
@provider_bp.route('/provider')
def provider_page():
    if session.get('role') != 'PROVIDER':
        return redirect('/login')

    return render_template("provider.html")


# ======================================================
# 📅 BOOKINGS (само неговите)
# ======================================================
@provider_bp.route('/provider/bookings')
def provider_bookings():
    if session.get('role') != 'PROVIDER':
        return jsonify({"error": "Unauthorized"}), 401

    provider_id = session.get('provider_id')
    date = request.args.get('date')

    query = Booking.query.filter_by(provider_id=provider_id)

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
# ✔ APPROVE / ❌ REJECT / 🗑 DELETE
# ======================================================
@provider_bp.route('/booking/<int:id>/approve', methods=['POST'])
def approve_booking_route(id):
    if session.get('role') != 'PROVIDER':
        return jsonify({"error": "Unauthorized"}), 401

    provider_id = session.get('provider_id')
    booking = Booking.query.get(id)

    if not booking:
        return jsonify({"error": "Няма запис"}), 404
    if booking.provider_id != provider_id:
        return jsonify({"error": "Forbidden"}), 403

    approve_booking(booking)
    record_booking_status(booking, "confirmed")
    log_action("PROVIDER_APPROVE", f"Booking {id} approved", provider_id)

    return jsonify({"message": "Approved"})


@provider_bp.route('/booking/<int:id>/reject', methods=['POST'])
def reject_booking_route(id):
    if session.get('role') != 'PROVIDER':
        return jsonify({"error": "Unauthorized"}), 401

    provider_id = session.get('provider_id')
    booking = Booking.query.get(id)

    if not booking:
        return jsonify({"error": "Няма запис"}), 404
    if booking.provider_id != provider_id:
        return jsonify({"error": "Forbidden"}), 403

    reject_booking(booking)
    record_booking_status(booking, "cancelled")
    log_action("PROVIDER_REJECT", f"Booking {id} rejected", provider_id)

    return jsonify({"message": "Rejected"})


@provider_bp.route('/booking/<int:id>/delete', methods=['POST'])
def delete_booking(id):
    if session.get('role') != 'PROVIDER':
        return jsonify({"error": "Unauthorized"}), 401

    provider_id = session.get('provider_id')
    booking = Booking.query.get(id)

    if not booking:
        return jsonify({"error": "Няма запис"}), 404
    if booking.provider_id != provider_id:
        return jsonify({"error": "Forbidden"}), 403

    db.session.delete(booking)
    db.session.commit()

    return jsonify({"message": "Deleted"})


@provider_bp.route('/provider/notifications')
def provider_notifications():
    if session.get('role') != 'PROVIDER':
        return jsonify({"error": "Unauthorized"}), 401

    count = Booking.query.filter_by(provider_id=session.get('provider_id'), status="PENDING").count()
    return jsonify({"pending_count": count})


@provider_bp.route('/provider/pending')
def provider_pending():
    if session.get('role') != 'PROVIDER':
        return jsonify({"error": "Unauthorized"}), 401

    provider_id = session.get('provider_id')
    bookings = Booking.query.filter_by(provider_id=provider_id, status="PENDING").order_by(Booking.start_time).all()

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


@provider_bp.route('/provider/schedule')
def provider_schedule():
    if session.get('role') != 'PROVIDER':
        return jsonify({"error": "Unauthorized"}), 401

    provider_id = session.get('provider_id')
    date = request.args.get('date')

    provider = Provider.query.get(provider_id)

    query = Booking.query.filter_by(provider_id=provider_id, status="CONFIRMED")

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
        "working_start": provider.working_start.strftime("%H:%M") if provider.working_start else "09:00",
        "working_end": provider.working_end.strftime("%H:%M") if provider.working_end else "19:00"
    })


@provider_bp.route('/provider/logout')
def provider_logout():
    session.clear()
    return redirect('/login')


@provider_bp.route('/subscribe', methods=['POST'])
def subscribe():
    if session.get('role') != 'PROVIDER':
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    provider_id = session.get('provider_id')

    existing = PushSubscription.query.filter_by(endpoint=data['endpoint']).first()
    if existing:
        return jsonify({"message": "Already subscribed"})

    sub = PushSubscription(
        provider_id=provider_id,
        endpoint=data['endpoint'],
        p256dh=data['keys']['p256dh'],
        auth=data['keys']['auth']
    )

    db.session.add(sub)
    db.session.commit()

    return jsonify({"message": "Subscribed"})


@provider_bp.route('/provider/available-slots')
def provider_available_slots():
    if session.get('role') != 'PROVIDER':
        return jsonify({"error": "Unauthorized"}), 401

    provider_id = session.get('provider_id')
    date = request.args.get('date')
    service_id = request.args.get('service_id')

    if not date or not service_id:
        return jsonify([])

    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        service_id = int(service_id)
    except:
        return jsonify([])

    provider = Provider.query.get(provider_id)
    service = Service.query.get(service_id)

    if not provider or not service:
        return jsonify([])

    return jsonify(generate_available_slots(provider, service, date_obj))


# ======================================================
# ➕ PROVIDER ADD BOOKING MANUALLY
# ======================================================
@provider_bp.route('/provider/add-booking', methods=['POST'])
def provider_add_booking():
    if session.get('role') != 'PROVIDER':
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}

    provider_id = session.get('provider_id')
    name = data.get('name', '').strip()
    phone = data.get('phone', '').strip().replace(" ", "")
    service_id = data.get('service_id')
    time_str = data.get('appointment_time')

    if not provider_id:
        return jsonify({"error": "Липсва provider session"}), 400
    if not name or not phone or not service_id or not time_str:
        return jsonify({"error": "Попълни всички полета"}), 400

    try:
        service_id = int(service_id)
        start_time = datetime.fromisoformat(time_str)
    except Exception:
        return jsonify({"error": "Невалидни данни"}), 400

    provider = Provider.query.get(provider_id)
    service = Service.query.get(service_id)

    if not provider:
        return jsonify({"error": "Невалиден служител"}), 400
    if not service:
        return jsonify({"error": "Невалидна услуга"}), 400
    if not provider_offers_service(provider_id, service_id):
        return jsonify({"error": "Служителят не предлага тази услуга"}), 400

    if not provider.working_days:
        provider.working_days = "1,2,3,4,5,6"
    if not provider.working_start:
        provider.working_start = time_cls(10, 0)
    if not provider.working_end:
        provider.working_end = time_cls(19, 0)

    db.session.commit()

    if start_time < sofia_now():
        return jsonify({"error": "Не можеш да добавиш минал час"}), 400

    slots = generate_available_slots(provider, service, start_time.date())
    if start_time.strftime("%H:%M") not in slots:
        return jsonify({"error": "Часът е зает или извън работното време"}), 400

    duration = get_effective_duration(provider_id, service)
    end_time = start_time + timedelta(minutes=duration)

    booking = Booking(
        user_name=name,
        user_phone=phone,
        user_email="",
        provider_id=provider_id,
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

    return jsonify({"message": "Часът е добавен", "id": booking.id}), 201


@provider_bp.route('/provider/settings', methods=['GET'])
def provider_settings():
    if session.get('role') != 'PROVIDER':
        return jsonify({"error": "Unauthorized"}), 401

    provider = Provider.query.get(session.get('provider_id'))
    if not provider:
        return jsonify({"error": "Няма такъв служител"}), 404

    return jsonify(get_schedule(provider))


@provider_bp.route('/provider/settings', methods=['PUT'])
def provider_update_settings():
    if session.get('role') != 'PROVIDER':
        return jsonify({"error": "Unauthorized"}), 401

    provider = Provider.query.get(session.get('provider_id'))
    if not provider:
        return jsonify({"error": "Няма такъв служител"}), 404

    try:
        result = update_schedule(provider, request.get_json(silent=True) or {})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    log_action("UPDATE_SCHEDULE", "Служител обнови своя график", provider.id)
    return jsonify(result)


@provider_bp.route('/provider/absences', methods=['GET'])
def provider_get_absences():
    if session.get('role') != 'PROVIDER':
        return jsonify({"error": "Unauthorized"}), 401

    return jsonify(list_absences(session.get('provider_id')))


@provider_bp.route('/provider/absences', methods=['POST'])
def provider_create_absence():
    if session.get('role') != 'PROVIDER':
        return jsonify({"error": "Unauthorized"}), 401

    provider_id = session.get('provider_id')

    try:
        absence, conflicts = create_absence(provider_id, request.get_json(silent=True) or {})
    except (ValueError, TypeError) as e:
        return jsonify({"error": str(e) or "Невалидни данни"}), 400

    log_action("CREATE_ABSENCE", f"{absence.reason} {absence.start_date}-{absence.end_date}", provider_id)
    return jsonify({"message": "OK", "id": absence.id, "conflicts": conflicts}), 201


@provider_bp.route('/provider/absences/<int:id>', methods=['DELETE'])
def provider_delete_absence(id):
    if session.get('role') != 'PROVIDER':
        return jsonify({"error": "Unauthorized"}), 401

    if not delete_absence(session.get('provider_id'), id):
        return jsonify({"error": "Няма такъв запис"}), 404

    return jsonify({"message": "Deleted"})


# ======================================================
# 🧾 КОИ УСЛУГИ ПРЕДЛАГАМ (self-service, по избор)
# ======================================================
@provider_bp.route('/provider/services')
def provider_my_services():
    if session.get('role') != 'PROVIDER':
        return jsonify({"error": "Unauthorized"}), 401

    provider = Provider.query.get(session.get('provider_id'))
    if not provider:
        return jsonify({"error": "Няма такъв служител"}), 404

    return jsonify([link.to_dict() for link in provider.service_links])