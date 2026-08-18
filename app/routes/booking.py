from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta
from app.extensions import db
from app.models import Booking, Service, Barber
import re
from app.services.email_service import send_booking_email
from app.services.booking_service import approve_booking, reject_booking
from app.services.booking_service import generate_available_slots
from flask import render_template
from app.services.push_service import send_push_to_barber
from app.metrics import record_booking_created
from app.utils.time_utils import sofia_now



booking_bp = Blueprint('booking', __name__)


# ======================================================
# 🔥 AVAILABILITY ENGINE
# ======================================================


@booking_bp.route('/availability')
def availability():
    barber_id = request.args.get('barber_id')
    date = request.args.get('date')
    service_id = request.args.get('service_id')

    if not barber_id or not date or not service_id:
        return jsonify([])

    try:
        barber_id = int(barber_id)
        service_id = int(service_id)
    except:
        return jsonify([])

    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    except:
        return jsonify([])

    barber = Barber.query.get(barber_id)
    service = Service.query.get(service_id)

    if not barber or not service:
        return jsonify([])

    # 🟡 working days safe
    if barber.working_days:
        weekday = date_obj.isoweekday()
        working_days = [int(d) for d in barber.working_days.split(",")]

        if weekday not in working_days:
            return jsonify([])

    # 🟡 working hours safe
    if not barber.working_start or not barber.working_end:
        return jsonify([])

    slots = generate_available_slots(barber, service, date_obj)
    return jsonify(slots)


@booking_bp.route('/privacy-policy')
def privacy_policy():
    return render_template('privacy.html')

# ======================================================
# 🔥 BOOK
# ======================================================
@booking_bp.route('/book', methods=['POST'])
def book():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Няма предоставени данни"}), 400

        # GDPR
        if not data.get('consent'):
            return jsonify({"error": "Трябва да се съгласите с обработката на лични данни"}), 400

        # INPUTS
        name = data.get('name', '').strip()
        phone = data.get('phone', '').strip().replace(" ", "")
        email = data.get('email', '').strip().lower()
        barber_id = data.get('barber_id')
        service_id = data.get('service_id')
        time_str = data.get('appointment_time')

        if not name or not phone or not barber_id or not service_id or not time_str:
            return jsonify({"error": "Попълни всички задължителни полета"}), 400

        # PHONE VALIDATION
        if not re.match(r'^(\+359|0)[0-9]{9}$', phone):
            return jsonify({"error": "Невалиден телефон"}), 400

        # EMAIL VALIDATION
        if email and not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return jsonify({"error": "Невалиден email"}), 400

        # DATETIME
        try:
            barber_id = int(barber_id)
            service_id = int(service_id)
            start_time = datetime.fromisoformat(time_str.replace("Z", ""))

            if start_time < sofia_now():
                return jsonify({"error": "Минал час"}), 400

        except:
            return jsonify({"error": "Невалидна дата"}), 400

        # DB
        service = Service.query.get(service_id)
        barber = Barber.query.get(barber_id)

        if not service or not barber:
            return jsonify({"error": "Невалидни данни"}), 400

        # AVAILABILITY
        date_obj = start_time.date()
        slots = generate_available_slots(barber, service, date_obj)

        if start_time.strftime("%H:%M") not in slots:
            return jsonify({"error": "Часът е зает"}), 400

        # SPAM (прост и безопасен)
        recent = Booking.query.filter(
            Booking.user_phone == phone
        ).order_by(Booking.id.desc()).first()

        active_bookings_count = Booking.query.filter(
         Booking.user_phone == phone,
         Booking.status.in_(["PENDING", "CONFIRMED"])
        ).count()

        if active_bookings_count >= 3:
         return jsonify({
        "error": "Можете да имате максимум 3 активни запазени часа"
         }), 400

        # CREATE
        end_time = start_time + timedelta(minutes=service.duration_minutes)

        booking = Booking(
            user_name=name,
            user_phone=phone,
            user_email=email,
            barber_id=barber_id,
            service_id=service_id,
            start_time=start_time,
            end_time=end_time,
            status="PENDING"
        )

        db.session.add(booking)
        db.session.commit()
        record_booking_created(booking)
        send_push_to_barber(
        barber_id,
          "Нов час",
         f"{name} запази час"
)

        return jsonify({"message": "OK", "id": booking.id}), 201

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": "Server error"}), 500
    




