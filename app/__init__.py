from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from apscheduler.schedulers.background import BackgroundScheduler
from flask import request, session
import os
from app.extensions import db
from dotenv import load_dotenv
from app.services.cleanup_service import cleanup_old_bookings
from datetime import datetime, timedelta
from app.models import Log
from app.utils.time_utils import sofia_now

last_cleanup = None
migrate = Migrate()
scheduler = BackgroundScheduler()


def start_scheduler(app):
    if scheduler.running:
        return

    # Защита само за локален dev сървър с debug=True (python run.py),
    # където Flask reloader-ът спауни втори процес.
    # Под gunicorn (production) app.debug е False, така че тази проверка се прескача.
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    from app.services.booking_service import send_upcoming_reminders

    def run_reminders():
        with app.app_context():
            try:
                send_upcoming_reminders()
            except Exception as e:
                print("❌ Reminder job error:", e)

    scheduler.add_job(run_reminders, 'interval', minutes=1, id='sms_reminders', replace_existing=True)
    scheduler.start()
    print("🔔 SMS reminder scheduler started")


def create_app():
    load_dotenv()
    app = Flask(__name__)

    app.config['SECRET_KEY'] = 'secret'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(os.getcwd(), 'barbershop.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    migrate.init_app(app, db)

    CORS(app)

    # 🔌 ROUTES
    from app.routes.main import main
    from app.routes.booking import booking_bp
    from app.routes.barber import barber_bp
    from app.routes.admin import admin_bp
    from app.routes.auth import auth_bp
    from app.routes.bulkgate_webhook import bulkgate_webhook

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(main)
    app.register_blueprint(booking_bp)
    app.register_blueprint(barber_bp)
    app.register_blueprint(bulkgate_webhook)

    @app.before_request
    def log_page_visit():
        if request.method != "GET":
            return

        path = request.path

        ignored_paths = (
            "/static/",
            "/sw.js",
            "/favicon.ico",
            "/admin/monitoring/stats",
        )

        if any(path.startswith(p) for p in ignored_paths):
            return

        if path.startswith("/api/"):
            return

        if path == "/admin/monitoring":
            return

        try:
            user_id = session.get("user_id")

            log = Log(
                user_id=user_id,
                action="VISIT",
                description=f"Посещение на {path}"
            )

            db.session.add(log)
            db.session.commit()

        except Exception as e:
            db.session.rollback()
            print("❌ Visit logging error:", e)

    # ✅ SW ROUTE (ВЪТРЕ в create_app)
    @app.route('/sw.js')
    def sw():
        return app.send_static_file('sw.js')

    # ✅ HEADER (ВЪТРЕ в create_app)
    @app.after_request
    def add_header(response):
        response.headers['Service-Worker-Allowed'] = '/'
        return response

    @app.before_request
    def auto_cleanup():
        global last_cleanup

        now = sofia_now()

        if not last_cleanup or (now - last_cleanup) > timedelta(hours=1):
            try:
                cleanup_old_bookings()
                last_cleanup = now
            except Exception as e:
                print("❌ Cleanup error:", e)

    start_scheduler(app)

    return app