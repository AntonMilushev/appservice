"""
Тестов скрипт за проверка на SMS известията през BulkGate.
Пуска се РЪЧНО от терминала, извън Flask приложението.

Изисква следните променливи в .env:
  SMS_APP_ID
  SMS_APP_TOKEN
  SMS_SENDER_NAME   (по избор, има default)

Изпълнение:
    python test_sms.py 0876515172 "Тестово съобщение от БръснаряТ"
"""

import sys
import os
import json
import logging
import requests
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.sms_service import _format_phone


def check_env():
    missing = [v for v in ["SMS_APP_ID", "SMS_APP_TOKEN"] if not os.getenv(v)]

    if missing:
        print("❌ Липсват следните променливи в .env:")
        for m in missing:
            print(f"   - {m}")
        sys.exit(1)

    print("✅ Всички нужни .env променливи са налични.")


def main():
    check_env()

    if len(sys.argv) >= 3:
        phone = sys.argv[1]
        text = sys.argv[2]
    else:
        phone = input("Телефон (напр. 0876515172): ").strip()
        text = input("Текст: ").strip() or "Тестово съобщение от БръснаряТ ✂️"

    formatted = _format_phone(phone)
    print(f"\n📩 Изпращам директно до: {formatted}")

    payload = {
        "application_id": os.getenv("SMS_APP_ID"),
        "application_token": os.getenv("SMS_APP_TOKEN"),
        "number": formatted,
        "text": text,
        "sender_id": "gText",
        "sender_id_value": os.getenv("SMS_SENDER_NAME", "БръснаряТ")
    }

    response = requests.post(
        "https://portal.bulkgate.com/api/1.0/simple/transactional",
        json=payload,
        timeout=10
    )

    print(f"\nHTTP STATUS: {response.status_code}")
    print("ПЪЛЕН ОТГОВОР:")
    try:
        print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    except Exception:
        print(response.text)


if __name__ == "__main__":
    main()