from kafka import KafkaConsumer
import json
import time
from config.settings import settings
from .notifier import send_alert

consumer = None

while consumer is None:
    try:
        print("Connecting to Fraud Topic...")
        consumer = KafkaConsumer(
            "fraud_alerts",
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVER,
            value_deserializer=lambda x: json.loads(x.decode("utf-8")),
            auto_offset_reset="earliest",
            group_id="fraud-alert-group"
        )
        print("Connected to fraud_alerts ✅")
    except:
        print("Retrying Kafka...")
        time.sleep(5)

print("🚨 Fraud Alert Service Started...")

for message in consumer:
    alert = message.value

    print("⚠️ ALERT RECEIVED:", alert)

    send_alert(alert)

    