from config.settings import settings
from kafka import KafkaConsumer, KafkaProducer
import sqlite3
import json
import time
import requests

from infrastructure.fraud_detection.engine import is_fraud
from infrastructure.fraud_detection.behavior import update_profile
from infrastructure.fraud_detection.anomaly import detect_anomaly
from infrastructure.fraud_detection.features import extract_features


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


consumer = create_consumer()
producer = create_producer()


# ================================
# 🗄 DATABASE SETUP (ONCE)
# ================================

conn = sqlite3.connect("events.db", check_same_thread=False)
cursor = conn.cursor()

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
    risk_level TEXT,
    risk_score INTEGER,
    timestamp TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS ml_features (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    event_type TEXT,
    device_type TEXT,
    ip TEXT,
    num_devices INTEGER,
    num_ips INTEGER,
    total_requests INTEGER,
    timestamp TEXT
)
""")

conn.commit()

print("🚀 Consumer + AI Fraud Engine started...")


# ================================
# 🔄 MAIN PROCESSING LOOP
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
        VALUES (?, ?, ?, ?, ?)
        """, (
            event["user_id"],
            event["event_type"],
            event["device_type"],
            event["ip"],
            event["timestamp"]
        ))

        # =========================
        # 🧠 BEHAVIOR PROFILING
        # =========================
        profile = update_profile(event)

        # =========================
        # 🔍 ANOMALY DETECTION
        # =========================
        anomaly_score, anomaly_reasons = detect_anomaly(event, profile)

        # =========================
        # ⚠️ RULE-BASED FRAUD
        # =========================
        fraud, rule_reason = is_fraud(event)

        # =========================
        # 🧠 FINAL AI SCORING
        # =========================
        final_score = anomaly_score + (50 if fraud else 0)

        if final_score >= 80:
            risk = "HIGH"
        elif final_score >= 50:
            risk = "MEDIUM"
        else:
            risk = "LOW"

        print(f"🧠 Score: {final_score} | Risk: {risk}")

        # =========================
        # 🤖 STORE ML FEATURES
        # =========================
        features = extract_features(event, profile)

        cursor.execute("""
        INSERT INTO ml_features (
            user_id, event_type, device_type, ip,
            num_devices, num_ips, total_requests, timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
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

        # =========================
        # 🚨 FRAUD HANDLING
        # =========================
        if risk == "HIGH":
            reason = ", ".join(anomaly_reasons) or rule_reason

            print("🚨 FRAUD DETECTED:", reason)

            cursor.execute("""
            INSERT INTO fraud_alerts (user_id, reason, risk_level, risk_score, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """, (
                event["user_id"],
                reason,
                risk,
                final_score,
                event["timestamp"]
            ))

            # 🔥 Send to fraud topic
            producer.send("fraud_alerts", {
                "user_id": event["user_id"],
                "risk": risk,
                "score": final_score,
                "reason": reason,
                "timestamp": event["timestamp"]
            })

            # 🔥 Notify dashboard
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

        else:
            print("✅ Normal event")

        # =========================
        # 💾 BATCH COMMIT (PERF)
        # =========================
        counter += 1
        if counter >= 5:
            conn.commit()
            counter = 0

    except Exception as e:
        print("❌ Error:", e)
        time.sleep(2)