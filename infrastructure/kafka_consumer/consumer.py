from config.settings import settings
from kafka import KafkaConsumer, KafkaProducer
import psycopg2
import json
import time
import requests

from infrastructure.fraud_detection.engine import is_fraud
from infrastructure.fraud_detection.behavior import update_profile
from infrastructure.fraud_detection.anomaly import detect_anomaly
from infrastructure.fraud_detection.features import extract_features
from infrastructure.ml.inference import predict_fraud

# ================================
# 🔁 KAFKA CONNECTION (RETRY SAFE)
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
            print("❌ Kafka not ready, retrying in 5 seconds...")
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
# 🗄 TABLE SETUP
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

cursor.execute("""
CREATE TABLE IF NOT EXISTS ml_features (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    event_type TEXT,
    device_type TEXT,
    ip TEXT,
    num_devices INTEGER,
    num_ips INTEGER,
    total_requests INTEGER,
    timestamp TIMESTAMP
)
""")

conn.commit()

print("🚀 Consumer + AI Fraud Engine started...")

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

        # STORE EVENT
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

        # BEHAVIOR
        profile = update_profile(event)

        # ANOMALY
        anomaly_score, anomaly_reasons = detect_anomaly(event, profile)

        # RULE
        fraud, rule_reason = is_fraud(event)

        # FEATURES
        features = extract_features(event, profile)

        # ML
        ml_anomaly, ml_score = predict_fraud(features)

        # SCORING
        rule_score = 50 if fraud else 0
        ml_score_scaled = 50 if ml_anomaly else 0

        final_score = rule_score + anomaly_score + ml_score_scaled

        if final_score >= 100:
            risk = "HIGH"
        elif final_score >= 60:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        print(f"🧠 Score: {final_score} | Risk: {risk}")

        # STORE FEATURES
        cursor.execute("""
        INSERT INTO ml_features (
            user_id, event_type, device_type, ip,
            num_devices, num_ips, total_requests, timestamp
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            features["user_id"],
            features["event_type"],
            features["device_type"],
            features["ip"],
            features["num_devices"],
            features["num_ips"],
            features["total_requests"],
            features["timestamp"]
        ))

        # FRAUD
        if risk == "HIGH":
            reason = ", ".join(anomaly_reasons) or rule_reason

            cursor.execute("""
            INSERT INTO fraud_alerts (user_id, reason, risk_level, risk_score, timestamp)
            VALUES (%s, %s, %s, %s, %s)
            """, (
                event["user_id"],
                reason,
                risk,
                final_score,
                event["timestamp"]
            ))

            producer.send("fraud_alerts", {
                "user_id": event["user_id"],
                "risk": risk,
                "score": final_score,
                "reason": reason,
                "timestamp": event["timestamp"]
            })

            try:
                requests.post(
                    "http://dashboard:8000/internal/fraud",
                    json={
                        "user_id": event["user_id"],
                        "risk_level": risk,
                        "risk_score": final_score,
                        "reason": reason,
                        "timestamp": event["timestamp"]
                    },
                    timeout=2
                )
            except Exception as e:
                print("⚠️ Dashboard unavailable:", e)

        counter += 1
        if counter >= 5:
            conn.commit()
            counter = 0

    except Exception as e:
        print("❌ Error:", e)
        time.sleep(2)