from flask import Blueprint, request, jsonify, render_template
from datetime import datetime, timedelta
from app.extensions import db
from app.models import Booking, Service, Provider
import re
from app.services.booking_service import (
    generate_available_slots, provider_offers_service,
    get_effective_duration, get_effective_price
)
from app.services.push_service import send_push_to_provider
from app.metrics import record_booking_created
from app.utils.time_utils import sofia_now


booking_bp = Blueprint('booking', __name__)


# ======================================================
# 🏪 PUBLIC CATALOG (за фронтенда — кои услуги/служители има)
# ======================================================
@booking_bp.route('/providers')
def public_providers():
    providers = Provider.query.filter_by(is_active=True).all()
    return jsonify([
        {"id": p.id, "name": p.name, "image": p.image}
        for p in providers
    ])


@booking_bp.route('/providers/<int:provider_id>/services')
def public_provider_services(provider_id):
    provider = Provider.query.get(provider_id)
    if not provider:
        return jsonify([])

    return jsonify([
        link.to_dict()
        for link in provider.service_links
        if link.service.is_active
    ])


# ======================================================
# 🔥 AVAILABILITY ENGINE
# ======================================================
@booking_bp.route('/availability')
def availability():
    provider_id = request.args.get('provider_id')
    date = request.args.get('date')
    service_id = request.args.get('service_id')

    if not provider_id or not date or not service_id:
        return jsonify([])

    try:
        provider_id = int(provider_id)
        service_id = int(service_id)
    except:
        return jsonify([])

    try:
        date_obj = datetime.strptime(date, "%Y-%m-%d").date()
    except:
        return jsonify([])

    provider = Provider.query.get(provider_id)
    service = Service.query.get(service_id)

    if not provider or not service:
        return jsonify([])

    if provider.working_days:
        weekday = date_obj.isoweekday()
        working_days = [int(d) for d in provider.working_days.split(",")]
        if weekday not in working_days:
            return jsonify([])

    if not provider.working_start or not provider.working_end:
        return jsonify([])

    slots = generate_available_slots(provider, service, date_obj)
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

        if not data.get('consent'):
            return jsonify({"error": "Трябва да се съгласите с обработката на лични данни"}), 400

        name = data.get('name', '').strip()
        phone = data.get('phone', '').strip().replace(" ", "")
        email = data.get('email', '').strip().lower()
        provider_id = data.get('provider_id')
        service_id = data.get('service_id')
        time_str = data.get('appointment_time')

        if not name or not phone or not provider_id or not service_id or not time_str:
            return jsonify({"error": "Попълни всички задължителни полета"}), 400

        if not re.match(r'^(\+359|0)[0-9]{9}$', phone):
            return jsonify({"error": "Невалиден телефон"}), 400

        if email and not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return jsonify({"error": "Невалиден email"}), 400

        try:
            provider_id = int(provider_id)
            service_id = int(service_id)
            start_time = datetime.fromisoformat(time_str.replace("Z", ""))

            if start_time < sofia_now():
                return jsonify({"error": "Минал час"}), 400
        except:
            return jsonify({"error": "Невалидна дата"}), 400

        service = Service.query.get(service_id)
        provider = Provider.query.get(provider_id)

        if not service or not provider:
            return jsonify({"error": "Невалидни данни"}), 400

        if not provider_offers_service(provider_id, service_id):
            return jsonify({"error": "Служителят не предлага тази услуга"}), 400

        date_obj = start_time.date()
        slots = generate_available_slots(provider, service, date_obj)

        if start_time.strftime("%H:%M") not in slots:
            return jsonify({"error": "Часът е зает"}), 400

        active_bookings_count = Booking.query.filter(
            Booking.user_phone == phone,
            Booking.status.in_(["PENDING", "CONFIRMED"])
        ).count()

        if active_bookings_count >= 3:
            return jsonify({"error": "Можете да имате максимум 3 активни запазени часа"}), 400

        duration = get_effective_duration(provider_id, service)
        price = get_effective_price(provider_id, service)
        end_time = start_time + timedelta(minutes=duration)

        booking = Booking(
            user_name=name,
            user_phone=phone,
            user_email=email,
            provider_id=provider_id,
            service_id=service_id,
            price=price,
            start_time=start_time,
            end_time=end_time,
            status="PENDING"
        )

        db.session.add(booking)
        db.session.commit()
        record_booking_created(booking)
        send_push_to_provider(provider_id, "Нов час", f"{name} запази час")

        return jsonify({"message": "OK", "id": booking.id}), 201

    except Exception as e:
        print("ERROR:", e)
        return jsonify({"error": "Server error"}), 500