import json
from pywebpush import webpush, WebPushException
from app.models.push_subscription import PushSubscription

VAPID_PUBLIC_KEY = "BGE376lp-3TNjXN_1GTsT_b4YbsDFsSDayDuHnaeaVWKjAtGaPmk9Y9OYmUydelfDkoJ6GWSu8K8WoQ8MKuIs7c"
VAPID_PRIVATE_KEY = "p8rrqLz-AT-VJt9yxjoBHlkmhF4KSx9Qnk2FJ60Z99U"

def send_push_to_barber(barber_id, title, body):
    subs = PushSubscription.query.filter_by(barber_id=barber_id).all()

    print("📡 FOUND SUBS:", len(subs))

    for sub in subs:
        try:
            print("➡️ SENDING TO:", sub.endpoint)

            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {
                        "p256dh": sub.p256dh,
                        "auth": sub.auth
                    }
                },
                data=json.dumps({
                    "title": title,
                    "body": body
                }),
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={
                    "sub": "mailto:admin@yourapp.com"
                }
            )

            print("✅ PUSH SENT")

        except WebPushException as e:
            print("❌ PUSH ERROR:", e)