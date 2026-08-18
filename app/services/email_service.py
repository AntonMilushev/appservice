import requests
import threading
import logging
import os

from flask import current_app

from app.utils.server_logger import logger


BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def _log_email(
    to_email,
    subject,
    status_type,
    booking_id,
    success,
    error=None
):
    try:
        from app.models.email_log import EmailLog
        from app.extensions import db

        entry = EmailLog(
            booking_id=booking_id,
            to_email=to_email,
            status_type=status_type,
            subject=subject,
            success=success,
            error=error
        )

        db.session.add(entry)
        db.session.commit()

    except Exception as e:
        logging.error(f"EMAIL LOG WRITE FAILED: {e}")
        logger.error(f"❌ EMAIL LOG WRITE FAILED: {e}")


def _send_email_request(
    to_email,
    subject,
    text_content,
    html_content=None,
    booking_id=None,
    status_type=None
):
    try:

        logger.info(
            f"📨 BREVO REQUEST START | "
            f"To: {to_email} | "
            f"Booking: {booking_id} | "
            f"Status: {status_type}"
        )

        logging.info(
            f"📨 BREVO REQUEST START | "
            f"To: {to_email} | "
            f"Booking: {booking_id} | "
            f"Status: {status_type}"
        )

        api_key = os.getenv("BREVO_API_KEY")

        if not api_key:

            message = (
                f"❌ BREVO_API_KEY is missing | "
                f"To: {to_email} | "
                f"Booking: {booking_id}"
            )

            logging.error(message)
            logger.error(message)

            _log_email(
                to_email,
                subject,
                status_type,
                booking_id,
                success=False,
                error="Missing BREVO_API_KEY"
            )

            return

        headers = {
            "accept": "application/json",
            "api-key": api_key,
            "content-type": "application/json"
        }

        payload = {
            "sender": {
                "email": os.getenv(
                    "MAIL_SENDER",
                    "brusnarqt97@gmail.com"
                ),
                "name": "БръснаряТ"
            },
            "to": [
                {
                    "email": to_email
                }
            ],
            "subject": subject,
            "textContent": text_content
        }

        if html_content:
            payload["htmlContent"] = html_content

        # ==========================================
        # BREVO REQUEST
        # ==========================================

        response = requests.post(
            BREVO_API_URL,
            json=payload,
            headers=headers,
            timeout=15
        )

        # ==========================================
        # BREVO RESPONSE
        # ==========================================

        logging.info(
            f"📨 BREVO STATUS: {response.status_code}"
        )

        logger.info(
            f"📨 BREVO STATUS: {response.status_code}"
        )

        logging.info(
            f"📨 BREVO RESPONSE: {response.text}"
        )

        logger.info(
            f"📨 BREVO RESPONSE: {response.text}"
        )

        # ==========================================
        # ERROR
        # ==========================================

        if response.status_code >= 400:

            error_message = (
                f"❌ BREVO ERROR | "
                f"HTTP: {response.status_code} | "
                f"To: {to_email} | "
                f"Response: {response.text}"
            )

            logging.error(error_message)
            logger.error(error_message)

            _log_email(
                to_email,
                subject,
                status_type,
                booking_id,
                success=False,
                error=(
                    f"HTTP {response.status_code}: "
                    f"{response.text[:200]}"
                )
            )

        # ==========================================
        # SUCCESS
        # ==========================================

        else:

            success_message = (
                f"📧 EMAIL SENT | "
                f"To: {to_email} | "
                f"Booking: {booking_id} | "
                f"Status: {status_type}"
            )

            logging.info(success_message)
            logger.info(success_message)

            _log_email(
                to_email,
                subject,
                status_type,
                booking_id,
                success=True
            )

        logger.info("📨 EMAIL REQUEST FINISHED")
        logging.info("📨 EMAIL REQUEST FINISHED")

    except Exception as e:

        error_message = (
            f"❌ EMAIL EXCEPTION | "
            f"To: {to_email} | "
            f"Booking: {booking_id} | "
            f"Error: {e}"
        )

        logging.exception(error_message)
        logger.exception(error_message)

        _log_email(
            to_email,
            subject,
            status_type,
            booking_id,
            success=False,
            error=str(e)
        )


# ==================================================
# ASYNC EMAIL
# ==================================================

def send_email_async(
    to_email,
    subject,
    text_content,
    html_content=None,
    booking_id=None,
    status_type=None
):

    if not to_email:
        return

    # Запазваме Flask application-а,
    # защото thread-ът няма автоматично context.
    app = current_app._get_current_object()

    logger.info(
        f"📨 EMAIL THREAD START | "
        f"To: {to_email} | "
        f"Booking: {booking_id} | "
        f"Status: {status_type}"
    )

    logging.info(
        f"📨 EMAIL THREAD START | "
        f"To: {to_email} | "
        f"Booking: {booking_id} | "
        f"Status: {status_type}"
    )

    thread = threading.Thread(
        target=_send_email_request_with_context,
        args=(
            app,
            to_email,
            subject,
            text_content,
            html_content,
            booking_id,
            status_type
        ),
        daemon=True
    )

    thread.start()


def _send_email_request_with_context(
    app,
    to_email,
    subject,
    text_content,
    html_content=None,
    booking_id=None,
    status_type=None
):

    with app.app_context():

        _send_email_request(
            to_email,
            subject,
            text_content,
            html_content,
            booking_id,
            status_type
        )


# ==================================================
# BUSINESS LOGIC
# ==================================================

def send_booking_email(
    to_email,
    status,
    name=None,
    start_time=None,
    booking_id=None
):

    if not to_email:
        return

    # ==========================================
    # ACCEPTED
    # ==========================================

    if status == "accepted" and start_time:

        subject = "Записът ви е приет"

        text = f"""
Здравей, {name}

Вашият час е потвърден.
Дата: {start_time.strftime('%d.%m.%Y')}
Час: {start_time.strftime('%H:%M')}
"""

        html = f"""
<h2>Здравей, {name}</h2>

<p>
Вашият час е <strong>потвърден</strong>.
</p>

<p>
📅 Дата: {start_time.strftime('%d.%m.%Y')}<br>
⏰ Час: {start_time.strftime('%H:%M')}
</p>
"""

    # ==========================================
    # REJECTED
    # ==========================================

    elif status == "rejected" and start_time:

        subject = "Записът ви е отказан"

        text = f"""
Здравей, {name}

За съжаление заявката ви беше отказана.

Дата: {start_time.strftime('%d.%m.%Y')}
Час: {start_time.strftime('%H:%M')}
"""

        html = f"""
<h2>Здравей, {name}</h2>

<p>
За съжаление вашият запис е <strong>отказан</strong>.
</p>

<p>
📅 Дата: {start_time.strftime('%d.%m.%Y')}<br>
⏰ Час: {start_time.strftime('%H:%M')}
</p>
"""

    # ==========================================
    # PENDING
    # ==========================================

    elif status == "pending" and start_time:

        subject = "Заявката е получена"

        text = f"""
Здравей, {name}

Заявката ви чака одобрение.

Дата: {start_time.strftime('%d.%m.%Y')}
Час: {start_time.strftime('%H:%M')}
"""

        html = f"""
<h2>Здравей, {name}</h2>

<p>
Заявката ви е получена и
<strong>чака одобрение</strong>.
</p>
"""

    else:
        return

    # ==========================================
    # STATUS
    # ==========================================

    logging.info(
        f"📧 STATUS: {status} | "
        f"To: {to_email} | "
        f"Booking: {booking_id}"
    )

    logger.info(
        f"📧 STATUS: {status} | "
        f"To: {to_email} | "
        f"Booking: {booking_id}"
    )

    send_email_async(
        to_email,
        subject,
        text,
        html,
        booking_id=booking_id,
        status_type=status
    )