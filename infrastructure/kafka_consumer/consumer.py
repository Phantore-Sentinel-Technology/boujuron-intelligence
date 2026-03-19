from config.settings import settings
from kafka import KafkaConsumer
import sqlite3
import json

from infrastructure.fraud_detection.engine import is_fraud

# ✅ Kafka consumer
consumer = KafkaConsumer(
    settings.KAFKA_TOPIC_EVENTS,
    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVER,
    value_deserializer=lambda x: json.loads(x.decode("utf-8")),
    auto_offset_reset="earliest",
    group_id="phantore-group"
)

# ✅ SQLite DB
conn = sqlite3.connect("events.db", check_same_thread=False)
cursor = conn.cursor()

# ✅ Create events table
cursor.execute("""
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    event_type TEXT,
    device_type TEXT,
    ip TEXT,
    timestamp TEXT
)
""")

# ✅ Create fraud alerts table
cursor.execute("""
CREATE TABLE IF NOT EXISTS fraud_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    reason TEXT,
    timestamp TEXT
)
""")

conn.commit()

print("🚀 Consumer + Fraud Engine started...")

# ✅ Process events
for message in consumer:
    event = message.value

    # STORE EVENT
    cursor.execute(
        """
        INSERT INTO events (user_id, event_type, device, ip, timestamp)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            event["user_id"],
            event["event_type"],
            event["device_type"],
            event["ip"],
            event["timestamp"]
        )
    )

    conn.commit()

    # FRAUD DETECTION
    fraud, reason = is_fraud(event)

    if fraud:
        print("🚨 FRAUD DETECTED:", event, "| Reason:", reason)

        cursor.execute(
            """
            INSERT INTO fraud_alerts (user_id, reason, timestamp)
            VALUES (?, ?, ?)
            """,
            (
                event["user_id"],
                reason,
                event["timestamp"]
            )
        )

        conn.commit()

    else:
        print("✅ Normal event:", event)
