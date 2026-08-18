from flask import Blueprint, jsonify, render_template, session, redirect, request
from app.extensions import db
from app.models import Booking, Barber, User
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


# ======================================================
# 📸 UPLOAD IMAGE
# ======================================================
@admin_bp.route('/admin/upload', methods=['POST'])
def upload_image():
    if session.get('role') != 'ADMIN':
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
    if session.get('role') != 'ADMIN':
        return redirect('/login')

    return render_template("admin.html")


# ======================================================
# 📊 DASHBOARD
# ======================================================
@admin_bp.route('/admin/dashboard')
def admin_dashboard():
    if session.get('role') != 'ADMIN':
        return jsonify({"error": "Unauthorized"}), 403

    # 🔥 взимаме дата от URL
    selected_date = request.args.get("date")

    # ако няма → днес
    if not selected_date:
        selected_date = sofia_now().strftime("%Y-%m-%d")

    barbers = Barber.query.all()
    result = []

    for barber in barbers:
        bookings = Booking.query.filter_by(barber_id=barber.id).all()

        filtered_bookings = []

        for b in bookings:
            booking_date = b.start_time.strftime("%Y-%m-%d")

            # 🔥 филтър по дата
            if booking_date == selected_date:
                filtered_bookings.append({
                    "id": b.id,
                    "name": b.user_name,
                    "service": b.service.name if b.service else "N/A",
                    "time": b.start_time.strftime("%Y-%m-%d %H:%M"),
                    "status": b.status
                })

        result.append({
            "barber": barber.name,
            "barber_id": barber.id,
            "bookings": filtered_bookings,
            "working_start": barber.working_start.strftime("%H:%M") if barber.working_start else "09:00",
            "working_end": barber.working_end.strftime("%H:%M") if barber.working_end else "19:00"
        })

    return jsonify(result)


# ======================================================
# ✔ APPROVE BOOKING
# ======================================================
@admin_bp.route('/admin/approve/<int:id>', methods=['POST'])
def approve_booking_route(id):
    if session.get('role') != 'ADMIN':
        return jsonify({"error": "Unauthorized"}), 403

    booking = db.session.get(Booking, id)

    if not booking:
        return jsonify({"error": "Няма запис"}), 404

    approve_booking(booking)

    log_action("APPROVE", f"Booking {booking.id} approved", booking.barber_id)

    return jsonify({"message": "Approved"})

# ======================================================
# ❌ REJECT BOOKING
# ======================================================
@admin_bp.route('/admin/reject/<int:id>', methods=['POST'])
def reject_booking_route(id):
    if session.get('role') != 'ADMIN':
        return jsonify({"error": "Unauthorized"}), 403

    booking = db.session.get(Booking, id)

    if not booking:
        return jsonify({"error": "Няма запис"}), 404

    reject_booking(booking)  # 👈 ТУК

    log_action("REJECT", f"Booking {booking.id} rejected", booking.barber_id)

    return jsonify({"message": "Rejected"})

# ======================================================
# 🗑 DELETE BOOKING
# ======================================================
@admin_bp.route('/admin/delete/<int:id>', methods=['POST'])
def delete_booking(id):
    if session.get('role') != 'ADMIN':
        return jsonify({"error": "Unauthorized"}), 403

    booking = db.session.get(Booking, id)

    if not booking:
        return jsonify({"error": "Няма запис"}), 404

    barber_id = booking.barber_id

    db.session.delete(booking)
    db.session.commit()

    log_action("DELETE_BOOKING", f"Booking {id} deleted", barber_id)

    return jsonify({"message": "Deleted"})


# ======================================================
# ➕ CREATE BARBER + USER (🔥 ВАЖНО)
# ======================================================
@admin_bp.route('/admin/barber', methods=['POST'])
def create_barber():
    if session.get('role') != 'ADMIN':
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json(silent=True) or {}

    name = data.get('name', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    image = data.get('image') or "/static/images/default.png"

    if not name or not username or not password:
        return jsonify({"error": "Всички полета са задължителни"}), 400

    existing = User.query.filter_by(username=username).first()
    if existing:
        return jsonify({"error": "Username вече съществува"}), 400

    barber = Barber(
        name=name,
        image=image,
        is_active=True,
        working_days="2,3,4,5,6",
        working_start=time(10, 0),
        working_end=time(19, 0),
        break_start=time(13, 0),
        break_end=time(14, 0)
    )

    db.session.add(barber)
    db.session.commit()

    user = User(
        username=username,
        password=generate_password_hash(password),
        role="BARBER",
        barber_id=barber.id
    )

    db.session.add(user)
    db.session.commit()

    log_action("CREATE_BARBER", f"{name} created with username {username}", barber.id)

    return jsonify({"message": "Created", "barber_id": barber.id})
# ======================================================
# 📥 READ BARBERS
# ======================================================
@admin_bp.route('/admin/barbers')
def get_barbers():
    if session.get('role') != 'ADMIN':
        return jsonify({"error": "Unauthorized"}), 403

    barbers = Barber.query.all()

    return jsonify([
        {
            "id": b.id,
            "name": b.name,
            "image": b.image
        }
        for b in barbers
    ])


# ======================================================
# ✏️ UPDATE BARBER
# ======================================================
@admin_bp.route('/admin/barber/<int:id>', methods=['PUT'])
def update_barber(id):
    if session.get('role') != 'ADMIN':
        return jsonify({"error": "Unauthorized"}), 403

    barber = Barber.query.get(id)

    if not barber:
        return jsonify({"error": "Not found"}), 404

    data = request.get_json(silent=True) or {}

    old_name = barber.name

    barber.name = data.get('name', barber.name)
    barber.image = data.get('image', barber.image)

    db.session.commit()

    log_action("UPDATE_BARBER", f"{old_name} → {barber.name}", barber.id)

    return jsonify({"message": "Updated"})


# ======================================================
# ❌ DELETE BARBER (🔥 FIX)
# ======================================================
@admin_bp.route('/admin/barber/<int:id>', methods=['DELETE'])
def delete_barber(id):
    if session.get('role') != 'ADMIN':
        return jsonify({"error": "Unauthorized"}), 403

    barber = Barber.query.get(id)

    if not barber:
        return jsonify({"error": "Not found"}), 404

    name = barber.name

    Booking.query.filter_by(barber_id=id).delete()
    User.query.filter_by(barber_id=id, role="BARBER").delete()

    db.session.delete(barber)
    db.session.commit()

    log_action("DELETE_BARBER", f"Barber {name} deleted", id)

    return jsonify({"message": "Deleted"})



@admin_bp.route('/admin/barber/<int:id>/settings', methods=['GET'])
def admin_get_barber_settings(id):
    if session.get('role') != 'ADMIN':
        return jsonify({"error": "Unauthorized"}), 403

    barber = Barber.query.get(id)
    if not barber:
        return jsonify({"error": "Not found"}), 404

    return jsonify(get_schedule(barber))


@admin_bp.route('/admin/barber/<int:id>/settings', methods=['PUT'])
def admin_update_barber_settings(id):
    if session.get('role') != 'ADMIN':
        return jsonify({"error": "Unauthorized"}), 403

    barber = Barber.query.get(id)
    if not barber:
        return jsonify({"error": "Not found"}), 404

    try:
        result = update_schedule(barber, request.get_json(silent=True) or {})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    log_action("UPDATE_SCHEDULE", f"Админ обнови графика на {barber.name}", barber.id)
    return jsonify(result)


@admin_bp.route('/admin/barber/<int:id>/absences', methods=['GET'])
def admin_get_barber_absences(id):
    if session.get('role') != 'ADMIN':
        return jsonify({"error": "Unauthorized"}), 403

    return jsonify(list_absences(id, include_past=True))


@admin_bp.route('/admin/barber/<int:id>/absences', methods=['POST'])
def admin_create_barber_absence(id):
    if session.get('role') != 'ADMIN':
        return jsonify({"error": "Unauthorized"}), 403

    barber = Barber.query.get(id)
    if not barber:
        return jsonify({"error": "Not found"}), 404

    try:
        absence, conflicts = create_absence(id, request.get_json(silent=True) or {})
    except (ValueError, TypeError) as e:
        return jsonify({"error": str(e) or "Невалидни данни"}), 400

    log_action("CREATE_ABSENCE", f"{barber.name}: {absence.reason} {absence.start_date}-{absence.end_date}", id)
    return jsonify({"message": "OK", "id": absence.id, "conflicts": conflicts}), 201


@admin_bp.route('/admin/absences/<int:id>', methods=['DELETE'])
def admin_delete_absence(id):
    if session.get('role') != 'ADMIN':
        return jsonify({"error": "Unauthorized"}), 403

    from app.models.barber_absence import BarberAbsence
    absence = BarberAbsence.query.get(id)
    if not absence:
        return jsonify({"error": "Not found"}), 404

    db.session.delete(absence)
    db.session.commit()
    return jsonify({"message": "Deleted"})


PER_PAGE = 10

@admin_bp.route('/admin/sms-logs')
def admin_sms_logs():
    if session.get('role') != 'ADMIN':
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

    logs = (
        query.order_by(SmsLog.created_at.desc())
        .offset((page - 1) * PER_PAGE)
        .limit(PER_PAGE)
        .all()
    )

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
    if session.get('role') != 'ADMIN':
        return jsonify({"error": "Unauthorized"}), 403

    log = SmsLog.query.get(id)
    if not log:
        return jsonify({"error": "Not found"}), 404

    db.session.delete(log)
    db.session.commit()

    return jsonify({"message": "Deleted"})


@admin_bp.route('/admin/sms-logs', methods=['DELETE'])
def admin_delete_sms_logs_bulk():
    if session.get('role') != 'ADMIN':
        return jsonify({"error": "Unauthorized"}), 403

    # изтрива всички логове, отговарящи на текущите филтри (или всички, ако няма филтри)
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
    if session.get('role') != 'ADMIN':
        return redirect('/login')

    return render_template("monitoring.html")


@admin_bp.route('/admin/monitoring/stats')
def monitoring_stats():
    if session.get('role') != 'ADMIN':
        return jsonify({"error": "Unauthorized"}), 403

    now = sofia_now()

    # ==========================================
    # ДНЕС - по българско време
    # ==========================================

    today = now.date()

    tomorrow = today + timedelta(days=1)

    day_start = datetime.combine(today, datetime.min.time())
    day_end = datetime.combine(tomorrow, datetime.min.time())

    # ==========================================
    # BOOKINGS
    # ==========================================

    # Колко заявки са създадени днес
    new_requests_today = Booking.query.filter(
        Booking.created_at >= day_start,
        Booking.created_at < day_end
    ).count()

    # Колко са потвърдени днес
    confirmed_today = Booking.query.filter(
        Booking.confirmed_at >= day_start,
        Booking.confirmed_at < day_end
    ).count()

    # Колко са отказани днес
    cancelled_today = Booking.query.filter(
        Booking.cancelled_at >= day_start,
        Booking.cancelled_at < day_end
    ).count()

    # Колко потвърдени часа има за днес
    confirmed_slots_today = Booking.query.filter(
        Booking.start_time >= day_start,
        Booking.start_time < day_end,
        Booking.status == "CONFIRMED"
    ).count()

    # Чакащи заявки в момента
    pending = Booking.query.filter(
        Booking.status == "PENDING"
    ).count()

    # ==========================================
    # SMS
    # ==========================================

    sms_day_ago = sofia_now() - timedelta(hours=24)

    sms_success = SmsLog.query.filter(
    SmsLog.created_at >= sms_day_ago,
    SmsLog.success == True
    ).count()

    sms_failed = SmsLog.query.filter(
    SmsLog.created_at >= sms_day_ago,
    SmsLog.success == False
    ).count()

    recent_sms_failures = SmsLog.query.filter(
    SmsLog.created_at >= sms_day_ago,
    SmsLog.success == False
    ).order_by(
    SmsLog.created_at.desc()
    ).limit(10).all()

    # ==========================================
    # EMAIL
    # ==========================================

    email_success = EmailLog.query.filter(
    EmailLog.created_at >= sms_day_ago,
    EmailLog.success == True
    ).count()

    email_failed = EmailLog.query.filter(
    EmailLog.created_at >= sms_day_ago,
    EmailLog.success == False
    ).count()

    recent_email_failures = EmailLog.query.filter(
    EmailLog.created_at >= sms_day_ago,
    EmailLog.success == False
    ).order_by(
    EmailLog.created_at.desc()
    ).limit(10).all()

    # ==========================================
    # ACTIVITY
    # ==========================================

    activity = Log.query.order_by(
        Log.created_at.desc()
    ).limit(20).all()

    return jsonify({

        # ======================================
        # BOOKINGS
        # ======================================

        "bookings": {
            # Нови заявки, направени днес
            "new_requests_today": new_requests_today,

            # Потвърдени днес
            "today_confirmed": confirmed_today,

            # Отказани днес
            "today_cancelled": cancelled_today,

            # Потвърдени часове, които са за днес
            "today_booked_hours": confirmed_slots_today,

            # Чакащи в момента
            "pending": pending,

            # Общо заявки, създадени днес
            "today_total": new_requests_today
        },

        # ======================================
        # SMS
        # ======================================

        "sms": {
            "success_24h": sms_success,
            "failed_24h": sms_failed,

            "recent_failures": [
                {
                    "phone": s.phone,
                    "status_type": s.status_type,
                    "error": s.error,
                    "created_at": s.created_at.strftime("%d.%m.%Y %H:%M")
                }
                for s in recent_sms_failures
            ]
        },

        # ======================================
        # EMAIL
        # ======================================

        "email": {
            "success_24h": email_success,
            "failed_24h": email_failed,

            "recent_failures": [
                {
                    "to_email": e.to_email,
                    "status_type": e.status_type,
                    "error": e.error,
                    "created_at": e.created_at.strftime("%d.%m.%Y %H:%M")
                }
                for e in recent_email_failures
            ]
        },

        # ======================================
        # ACTIVITY
        # ======================================

        "activity": [
            {
                "action": l.action,
                "description": l.description,
                "created_at": l.created_at.strftime("%d.%m.%Y %H:%M")
            }
            for l in activity
        ]
    })