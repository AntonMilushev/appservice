from prometheus_client import Counter, generate_latest, CONTENT_TYPE_LATEST
from flask import Response
from datetime import datetime
import pytz

TZ = pytz.timezone("Europe/Sofia")

page_views_total = Counter(
    "site_page_views_total",
    "Total site page views",
    ["path"]
)

booking_created_total = Counter(
    "booking_created_total",
    "Total created bookings",
    ["barber", "service", "hour"]
)

booking_status_total = Counter(
    "booking_status_total",
    "Booking status changes",
    ["status", "barber", "service"]
)


def record_page_view(path):
    page_views_total.labels(path=path).inc()


def record_booking_created(booking):
    hour = booking.start_time.astimezone(TZ).strftime("%H:00") if booking.start_time.tzinfo else booking.start_time.strftime("%H:00")

    booking_created_total.labels(
        barber=booking.barber.name,
        service=booking.service.name,
        hour=hour
    ).inc()


def record_booking_status(booking, status):
    booking_status_total.labels(
        status=status,
        barber=booking.barber.name,
        service=booking.service.name
    ).inc()


def metrics_response():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)