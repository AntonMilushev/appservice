from flask import Blueprint, jsonify, render_template, session, redirect, request
from app.extensions import db
from app.models import Booking, Provider, Service, ProviderService, User
from app.utils.logger import log_action
import os
import uuid
from datetime import time, datetime, timedelta
from app.utils.time_utils import sofia_now
from app.services.booking_service import approve_booking, reject_booking
from werkzeug.security import generate_password_hash
from app.services.schedule_service import (
    get_schedule, update_schedule, list_absences, create_absence, delete_absence
)
from app.models.sms_log import SmsLog
from app.models.email_log import EmailLog
from app.models.log import Log


admin_bp = Blueprint('admin', __name__)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '../static/uploads')


def _require_admin():
    return session.get('role') == 'ADMIN'


# ======================================================
# 📸 UPLOAD IMAGE
# ======================================================
@admin_bp.route('/admin/upload', methods=['POST'])
def upload_image():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    file = request.files.get('image')
    if not file:
        return jsonify({"error": "No file"}), 400

    filename = str(uuid.uuid4()) + "_" + file.filename
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)

    return jsonify({"url": f"/static/uploads/{filename}"})


# ======================================================
# 🧑‍💼 ADMIN PAGE
# ======================================================
@admin_bp.route('/admin')
def admin_page():
    if not _require_admin():
        return redirect('/login')

    return render_template("admin.html")


# ======================================================
# 📊 DASHBOARD
# ======================================================
@admin_bp.route('/admin/dashboard')
def admin_dashboard():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    selected_date = request.args.get("date") or sofia_now().strftime("%Y-%m-%d")

    providers = Provider.query.all()
    result = []

    for provider in providers:
        bookings = Booking.query.filter_by(provider_id=provider.id).all()
        filtered_bookings = []

        for b in bookings:
            booking_date = b.start_time.strftime("%Y-%m-%d")
            if booking_date == selected_date:
                filtered_bookings.append({
                    "id": b.id,
                    "name": b.user_name,
                    "service": b.service.name if b.service else "N/A",
                    "time": b.start_time.strftime("%Y-%m-%d %H:%M"),
                    "status": b.status
                })

        result.append({
            "provider": provider.name,
            "provider_id": provider.id,
            "bookings": filtered_bookings,
            "working_start": provider.working_start.strftime("%H:%M") if provider.working_start else "09:00",
            "working_end": provider.working_end.strftime("%H:%M") if provider.working_end else "19:00"
        })

    return jsonify(result)


# ======================================================
# ✔ APPROVE / ❌ REJECT / 🗑 DELETE BOOKING
# ======================================================
@admin_bp.route('/admin/approve/<int:id>', methods=['POST'])
def approve_booking_route(id):
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    booking = db.session.get(Booking, id)
    if not booking:
        return jsonify({"error": "Няма запис"}), 404

    approve_booking(booking)
    log_action("APPROVE", f"Booking {booking.id} approved", booking.provider_id)

    return jsonify({"message": "Approved"})


@admin_bp.route('/admin/reject/<int:id>', methods=['POST'])
def reject_booking_route(id):
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    booking = db.session.get(Booking, id)
    if not booking:
        return jsonify({"error": "Няма запис"}), 404

    reject_booking(booking)
    log_action("REJECT", f"Booking {booking.id} rejected", booking.provider_id)

    return jsonify({"message": "Rejected"})


@admin_bp.route('/admin/delete/<int:id>', methods=['POST'])
def delete_booking(id):
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    booking = db.session.get(Booking, id)
    if not booking:
        return jsonify({"error": "Няма запис"}), 404

    provider_id = booking.provider_id
    db.session.delete(booking)
    db.session.commit()

    log_action("DELETE_BOOKING", f"Booking {id} deleted", provider_id)
    return jsonify({"message": "Deleted"})


# ======================================================
# ➕ CREATE PROVIDER + USER LOGIN
# ======================================================
@admin_bp.route('/admin/provider', methods=['POST'])
def create_provider():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json(silent=True) or {}

    name = data.get('name', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    image = data.get('image') or "/static/images/default.png"

    if not name or not username or not password:
        return jsonify({"error": "Всички полета са задължителни"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username вече съществува"}), 400

    provider = Provider(
        name=name,
        image=image,
        is_active=True,
        working_days="1,2,3,4,5,6",
        working_start=time(10, 0),
        working_end=time(19, 0),
        break_start=time(13, 0),
        break_end=time(14, 0)
    )

    db.session.add(provider)
    db.session.commit()

    user = User(
        username=username,
        password=generate_password_hash(password),
        role="PROVIDER",
        provider_id=provider.id
    )

    db.session.add(user)
    db.session.commit()

    log_action("CREATE_PROVIDER", f"{name} created with username {username}", provider.id)

    return jsonify({"message": "Created", "provider_id": provider.id})


# ======================================================
# 📥 READ PROVIDERS
# ======================================================
@admin_bp.route('/admin/providers')
def get_providers():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    providers = Provider.query.all()
    return jsonify([{"id": p.id, "name": p.name, "image": p.image, "is_active": p.is_active} for p in providers])


# ======================================================
# ✏️ UPDATE PROVIDER
# ======================================================
@admin_bp.route('/admin/provider/<int:id>', methods=['PUT'])
def update_provider(id):
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    provider = Provider.query.get(id)
    if not provider:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json(silent=True) or {}
    old_name = provider.name

    provider.name = data.get('name', provider.name)
    provider.image = data.get('image', provider.image)
    if 'is_active' in data:
        provider.is_active = bool(data.get('is_active'))

    db.session.commit()

    log_action("UPDATE_PROVIDER", f"{old_name} → {provider.name}", provider.id)
    return jsonify({"message": "Updated"})


# ======================================================
# ❌ DELETE PROVIDER
# ======================================================
@admin_bp.route('/admin/provider/<int:id>', methods=['DELETE'])
def delete_provider(id):
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    provider = Provider.query.get(id)
    if not provider:
        return jsonify({"error": "Not found"}), 404

    name = provider.name

    Booking.query.filter_by(provider_id=id).delete()
    User.query.filter_by(provider_id=id, role="PROVIDER").delete()
    ProviderService.query.filter_by(provider_id=id).delete()

    db.session.delete(provider)
    db.session.commit()

    log_action("DELETE_PROVIDER", f"Provider {name} deleted", id)
    return jsonify({"message": "Deleted"})


@admin_bp.route('/admin/provider/<int:id>/settings', methods=['GET'])
def admin_get_provider_settings(id):
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    provider = Provider.query.get(id)
    if not provider:
        return jsonify({"error": "Not found"}), 404

    return jsonify(get_schedule(provider))


@admin_bp.route('/admin/provider/<int:id>/settings', methods=['PUT'])
def admin_update_provider_settings(id):
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    provider = Provider.query.get(id)
    if not provider:
        return jsonify({"error": "Not found"}), 404

    try:
        result = update_schedule(provider, request.get_json(silent=True) or {})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    log_action("UPDATE_SCHEDULE", f"Админ обнови графика на {provider.name}", provider.id)
    return jsonify(result)


@admin_bp.route('/admin/provider/<int:id>/absences', methods=['GET'])
def admin_get_provider_absences(id):
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    return jsonify(list_absences(id, include_past=True))


@admin_bp.route('/admin/provider/<int:id>/absences', methods=['POST'])
def admin_create_provider_absence(id):
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    provider = Provider.query.get(id)
    if not provider:
        return jsonify({"error": "Not found"}), 404

    try:
        absence, conflicts = create_absence(id, request.get_json(silent=True) or {})
    except (ValueError, TypeError) as e:
        return jsonify({"error": str(e) or "Невалидни данни"}), 400

    log_action("CREATE_ABSENCE", f"{provider.name}: {absence.reason} {absence.start_date}-{absence.end_date}", id)
    return jsonify({"message": "OK", "id": absence.id, "conflicts": conflicts}), 201


@admin_bp.route('/admin/absences/<int:id>', methods=['DELETE'])
def admin_delete_absence(id):
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    from app.models.provider_absence import ProviderAbsence
    absence = ProviderAbsence.query.get(id)
    if not absence:
        return jsonify({"error": "Not found"}), 404

    db.session.delete(absence)
    db.session.commit()
    return jsonify({"message": "Deleted"})


# ======================================================
# 🧾 SERVICE CATALOG (name, duration, base price)
# ======================================================
@admin_bp.route('/admin/services', methods=['GET'])
def admin_list_services():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    services = Service.query.all()
    return jsonify([
        {
            "id": s.id,
            "name": s.name,
            "duration_minutes": s.duration_minutes,
            "price": float(s.price) if s.price is not None else None,
            "is_active": s.is_active
        }
        for s in services
    ])


@admin_bp.route('/admin/services', methods=['POST'])
def admin_create_service():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    duration = data.get('duration_minutes')
    price = data.get('price')

    if not name or not duration:
        return jsonify({"error": "Име и времетраене са задължителни"}), 400

    try:
        duration = int(duration)
    except (TypeError, ValueError):
        return jsonify({"error": "Невалидно времетраене"}), 400

    service = Service(
        name=name,
        duration_minutes=duration,
        price=price if price not in (None, "") else None,
        is_active=True
    )

    db.session.add(service)
    db.session.commit()

    log_action("CREATE_SERVICE", f"{name} ({duration} мин)")
    return jsonify({"message": "Created", "id": service.id}), 201


@admin_bp.route('/admin/services/<int:id>', methods=['PUT'])
def admin_update_service(id):
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    service = Service.query.get(id)
    if not service:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json(silent=True) or {}

    if 'name' in data:
        service.name = data['name'].strip()
    if 'duration_minutes' in data:
        try:
            service.duration_minutes = int(data['duration_minutes'])
        except (TypeError, ValueError):
            return jsonify({"error": "Невалидно времетраене"}), 400
    if 'price' in data:
        service.price = data['price'] if data['price'] not in (None, "") else None
    if 'is_active' in data:
        service.is_active = bool(data['is_active'])

    db.session.commit()
    log_action("UPDATE_SERVICE", f"Service {id} updated")
    return jsonify({"message": "Updated"})


@admin_bp.route('/admin/services/<int:id>', methods=['DELETE'])
def admin_delete_service(id):
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    service = Service.query.get(id)
    if not service:
        return jsonify({"error": "Not found"}), 404

    ProviderService.query.filter_by(service_id=id).delete()
    db.session.delete(service)
    db.session.commit()

    log_action("DELETE_SERVICE", f"Service {id} deleted")
    return jsonify({"message": "Deleted"})


# ======================================================
# 🔗 PROVIDER <-> SERVICE (кой служител какво предлага + override цена/времетраене)
# ======================================================
@admin_bp.route('/admin/provider/<int:id>/services', methods=['GET'])
def admin_provider_services(id):
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    provider = Provider.query.get(id)
    if not provider:
        return jsonify({"error": "Not found"}), 404

    return jsonify([link.to_dict() for link in provider.service_links])


@admin_bp.route('/admin/provider/<int:id>/services', methods=['POST'])
def admin_assign_provider_service(id):
    """Добавя услуга на служителя. По избор: price / duration_minutes override."""
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    provider = Provider.query.get(id)
    if not provider:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json(silent=True) or {}
    service_id = data.get('service_id')

    if not service_id:
        return jsonify({"error": "Липсва service_id"}), 400

    service = Service.query.get(service_id)
    if not service:
        return jsonify({"error": "Невалидна услуга"}), 400

    existing = ProviderService.get(id, service_id)
    if existing:
        return jsonify({"error": "Служителят вече предлага тази услуга"}), 400

    link = ProviderService(
        provider_id=id,
        service_id=service_id,
        price=data.get('price') if data.get('price') not in (None, "") else None,
        duration_minutes=data.get('duration_minutes') if data.get('duration_minutes') not in (None, "") else None,
    )

    db.session.add(link)
    db.session.commit()

    log_action("ASSIGN_SERVICE", f"{provider.name} ← {service.name}", provider.id)
    return jsonify({"message": "Assigned", "id": link.id}), 201


@admin_bp.route('/admin/provider/<int:id>/services/<int:service_id>', methods=['PUT'])
def admin_update_provider_service(id, service_id):
    """Обновява override цена/времетраене за конкретен служител+услуга."""
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    link = ProviderService.get(id, service_id)
    if not link:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json(silent=True) or {}

    if 'price' in data:
        link.price = data['price'] if data['price'] not in (None, "") else None
    if 'duration_minutes' in data:
        link.duration_minutes = data['duration_minutes'] if data['duration_minutes'] not in (None, "") else None

    db.session.commit()
    return jsonify({"message": "Updated", **link.to_dict()})


@admin_bp.route('/admin/provider/<int:id>/services/<int:service_id>', methods=['DELETE'])
def admin_remove_provider_service(id, service_id):
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    link = ProviderService.get(id, service_id)
    if not link:
        return jsonify({"error": "Not found"}), 404

    db.session.delete(link)
    db.session.commit()

    return jsonify({"message": "Removed"})


# ======================================================
# 📜 SMS LOGS (непроменено)
# ======================================================
PER_PAGE = 10

@admin_bp.route('/admin/sms-logs')
def admin_sms_logs():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    phone = request.args.get('phone')
    status_type = request.args.get('status_type')
    success = request.args.get('success')

    try:
        page = int(request.args.get('page', 1))
        if page < 1:
            page = 1
    except ValueError:
        page = 1

    query = SmsLog.query

    if phone:
        query = query.filter(SmsLog.phone.contains(phone))
    if status_type:
        query = query.filter_by(status_type=status_type)
    if success in ("true", "false"):
        query = query.filter_by(success=(success == "true"))

    total = query.count()
    logs = query.order_by(SmsLog.created_at.desc()).offset((page - 1) * PER_PAGE).limit(PER_PAGE).all()

    return jsonify({
        "items": [
            {
                "id": l.id,
                "booking_id": l.booking_id,
                "phone": l.phone,
                "status_type": l.status_type,
                "message": l.message,
                "success": l.success,
                "provider_sms_id": l.provider_sms_id,
                "error": l.error,
                "created_at": l.created_at.strftime("%Y-%m-%d %H:%M:%S")
            }
            for l in logs
        ],
        "page": page,
        "per_page": PER_PAGE,
        "total": total,
        "total_pages": max(1, (total + PER_PAGE - 1) // PER_PAGE)
    })


@admin_bp.route('/admin/sms-logs/<int:id>', methods=['DELETE'])
def admin_delete_sms_log(id):
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    log = SmsLog.query.get(id)
    if not log:
        return jsonify({"error": "Not found"}), 404

    db.session.delete(log)
    db.session.commit()
    return jsonify({"message": "Deleted"})


@admin_bp.route('/admin/sms-logs', methods=['DELETE'])
def admin_delete_sms_logs_bulk():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    phone = request.args.get('phone')
    status_type = request.args.get('status_type')
    success = request.args.get('success')

    query = SmsLog.query

    if phone:
        query = query.filter(SmsLog.phone.contains(phone))
    if status_type:
        query = query.filter_by(status_type=status_type)
    if success in ("true", "false"):
        query = query.filter_by(success=(success == "true"))

    deleted_count = query.delete(synchronize_session=False)
    db.session.commit()

    log_action("DELETE_SMS_LOGS", f"Изтрити {deleted_count} SMS лог записа")
    return jsonify({"message": "Deleted", "count": deleted_count})


@admin_bp.route('/admin/monitoring')
def monitoring_page():
    if not _require_admin():
        return redirect('/login')

    return render_template("monitoring.html")


@admin_bp.route('/admin/monitoring/stats')
def monitoring_stats():
    if not _require_admin():
        return jsonify({"error": "Unauthorized"}), 403

    now = sofia_now()
    today = now.date()
    tomorrow = today + timedelta(days=1)

    day_start = datetime.combine(today, datetime.min.time())
    day_end = datetime.combine(tomorrow, datetime.min.time())

    new_requests_today = Booking.query.filter(
        Booking.created_at >= day_start, Booking.created_at < day_end
    ).count()

    confirmed_today = Booking.query.filter(
        Booking.confirmed_at >= day_start, Booking.confirmed_at < day_end
    ).count()

    cancelled_today = Booking.query.filter(
        Booking.cancelled_at >= day_start, Booking.cancelled_at < day_end
    ).count()

    confirmed_slots_today = Booking.query.filter(
        Booking.start_time >= day_start, Booking.start_time < day_end, Booking.status == "CONFIRMED"
    ).count()

    pending = Booking.query.filter(Booking.status == "PENDING").count()

    sms_day_ago = sofia_now() - timedelta(hours=24)

    sms_success = SmsLog.query.filter(SmsLog.created_at >= sms_day_ago, SmsLog.success == True).count()
    sms_failed = SmsLog.query.filter(SmsLog.created_at >= sms_day_ago, SmsLog.success == False).count()
    recent_sms_failures = SmsLog.query.filter(
        SmsLog.created_at >= sms_day_ago, SmsLog.success == False
    ).order_by(SmsLog.created_at.desc()).limit(10).all()

    email_success = EmailLog.query.filter(EmailLog.created_at >= sms_day_ago, EmailLog.success == True).count()
    email_failed = EmailLog.query.filter(EmailLog.created_at >= sms_day_ago, EmailLog.success == False).count()
    recent_email_failures = EmailLog.query.filter(
        EmailLog.created_at >= sms_day_ago, EmailLog.success == False
    ).order_by(EmailLog.created_at.desc()).limit(10).all()

    activity = Log.query.order_by(Log.created_at.desc()).limit(20).all()

    return jsonify({
        "bookings": {
            "new_requests_today": new_requests_today,
            "today_confirmed": confirmed_today,
            "today_cancelled": cancelled_today,
            "today_booked_hours": confirmed_slots_today,
            "pending": pending,
            "today_total": new_requests_today
        },
        "sms": {
            "success_24h": sms_success,
            "failed_24h": sms_failed,
            "recent_failures": [
                {
                    "phone": s.phone,
                    "status_type": s.status_type,
                    "error": s.error,
                    "created_at": s.created_at.strftime("%d.%m.%Y %H:%M")
                } for s in recent_sms_failures
            ]
        },
        "email": {
            "success_24h": email_success,
            "failed_24h": email_failed,
            "recent_failures": [
                {
                    "to_email": e.to_email,
                    "status_type": e.status_type,
                    "error": e.error,
                    "created_at": e.created_at.strftime("%d.%m.%Y %H:%M")
                } for e in recent_email_failures
            ]
        },
        "activity": [
            {
                "action": l.action,
                "description": l.description,
                "created_at": l.created_at.strftime("%d.%m.%Y %H:%M")
            } for l in activity
        ]
    })