from flask import Blueprint, render_template, request
from datetime import datetime
from app.models import Provider, Service
from app.metrics import metrics_response, record_page_view
from app.utils.time_utils import sofia_today

main = Blueprint('main', __name__)


@main.before_app_request
def track_page_views():
    if request.path.startswith("/static"):
        return
    if request.path in ["/metrics", "/sw.js", "/manifest.json"]:
        return

    record_page_view(request.path)

@main.route('/')
def index():
    return render_template(
        'index.html',
        provider=Provider.query.filter_by(is_active=True).all(),
        services=Service.query.all(),
        today=sofia_today()
    )

@main.route("/metrics")
def metrics():
    return metrics_response()