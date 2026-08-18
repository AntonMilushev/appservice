from flask import Blueprint, request, jsonify
from datetime import datetime
import json

from app.extensions import db
from app.models.sms_log import SmsLog
from app.utils.server_logger import logger
from app.utils.time_utils import sofia_now


bulkgate_webhook = Blueprint(
    "bulkgate_webhook",
    __name__,
    url_prefix="/api/bulkgate"
)


@bulkgate_webhook.route("/delivery", methods=["POST"])
def bulkgate_delivery():

    try:
        data = request.get_json(silent=True)

        if not data:
            logger.warning(
                "⚠️ BULKGATE WEBHOOK: Empty payload"
            )

            return jsonify({
                "success": False,
                "error": "Empty payload"
            }), 400

        logger.info(
            "📨 BULKGATE DELIVERY WEBHOOK:\n%s",
            json.dumps(data, ensure_ascii=False)
        )

        # Засега проверяваме възможните полета.
        # След като видим реалния BulkGate payload,
        # ще го направим точно според него.
        sms_id = (
            data.get("sms_id")
            or data.get("message_id")
            or data.get("id")
        )

        status = (
            data.get("status")
            or data.get("delivery_status")
        )

        if not sms_id:
            logger.warning(
                "⚠️ BULKGATE WEBHOOK: SMS ID missing | Payload: %s",
                data
            )

            return jsonify({
                "success": False,
                "error": "SMS ID missing"
            }), 400

        sms_log = SmsLog.query.filter_by(
            provider_sms_id=str(sms_id)
        ).first()

        if not sms_log:
            logger.warning(
                "⚠️ BULKGATE WEBHOOK: SMS not found | ID: %s",
                sms_id
            )

            return jsonify({
                "success": False,
                "error": "SMS not found"
            }), 200

        sms_log.provider_status = status

        if status == "delivered":

            sms_log.delivered_at = datetime.sofia_now()
            sms_log.success = True

            logger.info(
                "✅ SMS DELIVERED | "
                "SMS ID: %s | "
                "Booking: %s | "
                "Phone: %s",
                sms_id,
                sms_log.booking_id,
                sms_log.phone
            )

        elif status in (
            "not_delivered",
            "unavailable",
            "error",
            "failed"
        ):

            sms_log.success = False

            logger.warning(
                "❌ SMS NOT DELIVERED | "
                "SMS ID: %s | "
                "Status: %s | "
                "Booking: %s",
                sms_id,
                status,
                sms_log.booking_id
            )

        else:

            logger.info(
                "📱 SMS STATUS UPDATE | "
                "SMS ID: %s | "
                "Status: %s | "
                "Booking: %s",
                sms_id,
                status,
                sms_log.booking_id
            )

        db.session.commit()

        return jsonify({
            "success": True
        }), 200

    except Exception as e:

        db.session.rollback()

        logger.exception(
            "❌ BULKGATE WEBHOOK ERROR: %s",
            e
        )

        return jsonify({
            "success": False
        }), 500