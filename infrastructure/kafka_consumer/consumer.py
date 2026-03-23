from config.settings import settings
from kafka import KafkaConsumer
import sqlite3
import json
import time

from infrastructure.fraud_detection.engine import is_fraud

# ✅ Kafka connection retry
consumer = None

while consumer is None:
    try:
        print(f"Connecting to Kafka at {settings.KAFKA_BOOTSTRAP_SERVER}...")
        consumer = KafkaConsumer(
            settings.KAFKA_TOPIC_EVENTS,
            bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVER,
            value_deserializer=lambda x: json.loads(x.decode("utf-8")),
            auto_offset_reset="earliest",
            group_id="phantore-group"
        )
        print("Connected to Kafka ✅")
    except Exception:
        print("Kafka not ready, retrying in 5 seconds...")
        time.sleep(5)

# ✅ SQLite DB
conn = sqlite3.connect("events.db", check_same_thread=False)
cursor = conn.cursor()

# Tables
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

counter = 0

while True:
    try:
        msg = consumer.poll(timeout_ms=1000)

        if msg is None:
            continue

        print("📥 MESSAGE RECEIVED")

        # ✅ CORRECT: get actual event data
        event = msg.value

        # STORE EVENT
        cursor.execute(
            """
            INSERT INTO events (user_id, event_type, device_type, ip, timestamp)
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

        # FRAUD DETECTION
        fraud, reason = is_fraud(event)

        if fraud:
            print("🚨 FRAUD DETECTED:", reason)

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
        else:
            print("✅ Normal event")

        counter += 1

        if counter >= 5:
            conn.commit()
            counter = 0

    except Exception as e:
        print("❌ Error processing message:", e)
        time.sleep(2)