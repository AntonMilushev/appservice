import requests
import threading
import logging
import os

from flask import current_app
from app.utils.server_logger import logger


BULKGATE_URL = "https://portal.bulkgate.com/api/1.0/simple/transactional"


def _format_phone(phone):
    phone = phone.strip().replace(" ", "")

    if phone.startswith("+"):
        phone = phone[1:]
    elif phone.startswith("0"):
        phone = "359" + phone[1:]

    return phone


def _log_sms(
    booking_id,
    phone,
    status_type,
    message,
    success,
    provider_sms_id=None,
    provider_response=None,
    error=None
):
    try:
        from app.models.sms_log import SmsLog
        from app.extensions import db

        entry = SmsLog(
            booking_id=booking_id,
            phone=phone,
            status_type=status_type,
            message=message,
            success=success,
            provider_sms_id=provider_sms_id,
            provider_response=provider_response,
            error=error
        )

        db.session.add(entry)
        db.session.commit()

    except Exception as e:
        logging.error(f"SMS LOG WRITE FAILED: {e}")
        logger.error(f"❌ SMS LOG WRITE FAILED: {e}")


def _send_sms_request(app, to_phone, text, booking_id=None, status_type=None):

    with app.app_context():

        try:
            app_id = os.getenv("SMS_APP_ID")
            app_token = os.getenv("SMS_APP_TOKEN")
            sender_name = os.getenv("SMS_SENDER_NAME", "BrusnaryaT")

            if not app_id or not app_token:

                message = (
                    f"⚠️ SMS_APP_ID/SMS_APP_TOKEN липсват — "
                    f"SMS НЕ е изпратен | "
                    f"Phone: {to_phone} | "
                    f"Booking: {booking_id}"
                )

                # Application log
                logging.warning(message)

                # File log
                logger.warning(message)

                _log_sms(
                    booking_id,
                    to_phone,
                    status_type,
                    text,
                    success=False,
                    error="Missing SMS_APP_ID/SMS_APP_TOKEN"
                )

                return

            phone = _format_phone(to_phone)

            payload = {
                "application_id": app_id,
                "application_token": app_token,
                "number": phone,
                "text": text,
                "sender_id": "gText",
                "sender_id_value": sender_name,
                "unicode": True
            }

            # -----------------------------
            # REQUEST
            # -----------------------------

            logging.info(
                f"📨 BULKGATE REQUEST | "
                f"Phone: {phone} | "
                f"Booking: {booking_id}"
            )

            logger.info(
                f"📨 BULKGATE REQUEST | "
                f"Phone: {phone} | "
                f"Booking: {booking_id} | "
                f"Status: {status_type}"
            )

            response = requests.post(
                BULKGATE_URL,
                json=payload,
                timeout=10
            )

            data = response.json()

            # -----------------------------
            # ERROR
            # -----------------------------

            if response.status_code >= 400 or "error" in data:

                error_message = (
                    f"❌ BULKGATE ERROR | "
                    f"HTTP: {response.status_code} | "
                    f"Phone: {phone} | "
                    f"Response: {response.text}"
                )

                # Application console
                logging.error(error_message)

                # File
                logger.error(error_message)

                _log_sms(
                    booking_id,
                    phone,
                    status_type,
                    text,
                    success=False,
                    provider_response=response.text,
                    error=f"HTTP {response.status_code}"
                )

            # -----------------------------
            # SUCCESS
            # -----------------------------

            else:

                sms_id = data.get("data", {}).get("sms_id")

                success_message = (
                    f"📨 BULKGATE STATUS: {response.status_code}\n"
                    f"📨 BULKGATE SMS ID: {sms_id}\n"
                    f"📨 BULKGATE RESPONSE: {response.text}"
                )

                # Application console
                logging.info(success_message)

                # File
                logger.info(success_message)

                _log_sms(
                    booking_id,
                    phone,
                    status_type,
                    text,
                    success=True,
                    provider_sms_id=str(sms_id) if sms_id else None,
                    provider_response=response.text
                )

        except Exception as e:

            error_message = (
                f"❌ SMS EXCEPTION | "
                f"Phone: {to_phone} | "
                f"Booking: {booking_id} | "
                f"Error: {e}"
            )

            # Application console
            logging.exception(error_message)

            # File
            logger.exception(error_message)

            _log_sms(
                booking_id,
                to_phone,
                status_type,
                text,
                success=False,
                error=str(e)
            )


def send_sms_async(
    to_phone,
    text,
    booking_id=None,
    status_type=None
):

    if not to_phone:
        return

    app = current_app._get_current_object()

    thread = threading.Thread(
        target=_send_sms_request,
        args=(
            app,
            to_phone,
            text,
            booking_id,
            status_type
        ),
        daemon=True
    )

    thread.start()


# =========================
# BUSINESS LOGIC
# =========================

def send_booking_sms(
    to_phone,
    status,
    name=None,
    start_time=None,
    booking_id=None
):

    if not to_phone:
        return

    if status == "accepted" and start_time:

        text = (
            f"{name}, часът Ви е потвърден:"
            f"{start_time.strftime('%d.%m/ %H:%M')}. "
            f"БръснаряТ"
        )

    elif status == "rejected" and start_time:

        text = (
            f"{name}, часът Ви е отказан:"
            f"{start_time.strftime('%d.%m/ %H:%M')}. "
            f"БръснаряТ"
        )

    elif status == "pending" and start_time:

        text = (
            f"{name}, заявка "
            f"{start_time.strftime('%d.%m/ %H:%M')} "
            f"чака одобрение. БръснаряТ"
        )

    elif status == "reminder" and start_time:

        text = (
            f"{name}, напомняне: Имате час днес "
            f"{start_time.strftime('%H:%M')} "
            f"при БръснаряТ"
        )

    else:
        return

    # Application console
    logging.info(
        f"📩 SMS STATUS: {status} | "
        f"Phone: {to_phone} | "
        f"Booking: {booking_id}"
    )

    # File log
    logger.info(
        f"📩 SMS STATUS: {status} | "
        f"Phone: {to_phone} | "
        f"Booking: {booking_id}"
    )

    send_sms_async(
        to_phone,
        text,
        booking_id=booking_id,
        status_type=status
    )