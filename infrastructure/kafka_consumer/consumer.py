from config.settings import settings
from kafka import KafkaConsumer, KafkaProducer
import psycopg2
import json
import time
import requests

from infrastructure.risk_engine.engine import process_event

# ================================
# 🔁 KAFKA CONNECTION
# ================================

def create_consumer():
    while True:
        try:
            print(f"Connecting to Kafka at {settings.KAFKA_BOOTSTRAP_SERVER}...")
            consumer = KafkaConsumer(
                settings.KAFKA_TOPIC_EVENTS,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVER,
                value_deserializer=lambda x: json.loads(x.decode("utf-8")),
                auto_offset_reset="earliest",
                group_id="phantore-group"
            )
            print("✅ Kafka Consumer Connected")
            return consumer
        except Exception:
            print("❌ Kafka not ready, retrying...")
            time.sleep(5)


def create_producer():
    while True:
        try:
            producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVER,
                value_serializer=lambda v: json.dumps(v).encode("utf-8")
            )
            print("✅ Kafka Producer Connected")
            return producer
        except Exception:
            print("❌ Kafka producer retrying...")
            time.sleep(5)


def create_db():
    while True:
        try:
            print("Connecting to PostgreSQL...")
            conn = psycopg2.connect(settings.DATABASE_URL)
            print("✅ PostgreSQL Connected")
            return conn, conn.cursor()
        except Exception:
            print("❌ Postgres not ready, retrying...")
            time.sleep(5)


consumer = create_consumer()
producer = create_producer()
conn, cursor = create_db()

# ================================
# 🗄 TABLES
# ================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    event_type TEXT,
    device_type TEXT,
    ip TEXT,
    timestamp TIMESTAMP
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS fraud_alerts (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    reason TEXT,
    risk_level TEXT,
    risk_score INTEGER,
    timestamp TIMESTAMP
)
""")

conn.commit()

print("🚀 Consumer + Risk Engine started...")

# ================================
# 🔄 MAIN LOOP
# ================================

counter = 0

while True:
    try:
        msg = consumer.poll(timeout_ms=1000)
        if msg is None:
            continue

        event = msg.value
        print("📥 EVENT:", event)

        # =========================
        # 📥 STORE RAW EVENT
        # =========================
        cursor.execute("""
        INSERT INTO events (user_id, event_type, device_type, ip, timestamp)
        VALUES (%s, %s, %s, %s, %s)
        """, (
            event["user_id"],
            event["event_type"],
            event["device_type"],
            event["ip"],
            event["timestamp"]
        ))

        # =========================
        # 🧠 PROCESS WITH RISK ENGINE
        # =========================
        result = process_event(event)

        print("🧠 RESULT:", result)

        # =========================
        # 🚨 HANDLE FRAUD
        # =========================
        if result["risk_level"] == "HIGH":

            cursor.execute("""
            INSERT INTO fraud_alerts (user_id, reason, risk_level, risk_score, timestamp)
            VALUES (%s, %s, %s, %s, %s)
            """, (
                result["user_id"],
                ", ".join(result["reasons"]),
                result["risk_level"],
                result["risk_score"],
                result["timestamp"]
            ))

            # 🔥 Send to Kafka fraud topic
            producer.send("fraud_alerts", result)

            # 🔥 Notify dashboard
            try:
                requests.post(
                    "http://dashboard:8000/internal/fraud",
                    json=result,
                    timeout=2
                )
            except Exception as e:
                print("⚠️ Dashboard unavailable:", e)

        else:
            print("✅ Normal event")

        # =========================
        # 💾 COMMIT (BATCH)
        # =========================
        counter += 1
        if counter >= 5:
            conn.commit()
            counter = 0

    except Exception as e:
        print("❌ Error:", e)
        time.sleep(2)