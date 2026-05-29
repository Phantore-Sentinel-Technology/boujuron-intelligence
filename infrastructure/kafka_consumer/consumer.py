from config.settings import settings
from kafka import KafkaConsumer, KafkaProducer
import psycopg2
import json
import time
import requests

from infrastructure.fraud_detection.ai_engine import analyze_event

# ==================================================
# KAFKA CONNECTION
# ==================================================

def create_consumer():
    while True:
        try:
            print(f"Connecting to Kafka at {settings.KAFKA_BOOTSTRAP_SERVER}...")

            consumer = KafkaConsumer(
                settings.KAFKA_TOPIC_EVENTS,
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVER,
                value_deserializer=lambda x: json.loads(x.decode("utf-8")),
                auto_offset_reset="latest",
                enable_auto_commit=True,
                group_id="boujuron-group"
            )

            print("✅ Kafka Consumer Connected")
            return consumer

        except Exception as e:
            print(f"❌ Kafka Consumer Error: {e}")
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

        except Exception as e:
            print(f"❌ Kafka Producer Error: {e}")
            time.sleep(5)


# ==================================================
# DATABASE CONNECTION
# ==================================================

def create_db():
    while True:
        try:
            print("Connecting to PostgreSQL...")

            conn = psycopg2.connect(settings.DATABASE_URL)
            cursor = conn.cursor()

            print("✅ PostgreSQL Connected")
            return conn, cursor

        except Exception as e:
            print(f"❌ PostgreSQL Error: {e}")
            time.sleep(5)


consumer = create_consumer()
producer = create_producer()
conn, cursor = create_db()

# ==================================================
# TABLES
# ==================================================

cursor.execute("""
CREATE TABLE IF NOT EXISTS events (
    id SERIAL PRIMARY KEY,
    transaction_id TEXT,
    user_id TEXT,
    amount NUMERIC,
    location TEXT,
    event_type TEXT,
    device_type TEXT,
    network TEXT,
    ip TEXT,
    timestamp TIMESTAMP
)
""")

cursor.execute("""
    ALTER TABLE events
    ADD COLUMN IF NOT EXISTS network TEXT
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS fraud_alerts (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    reason TEXT,
    risk_level TEXT,
    risk_score INTEGER,
    recommended_action TEXT,
    confidence NUMERIC,
    signals_triggered INTEGER,
    behavioral_match BOOLEAN,
    timestamp TIMESTAMP
)
""")

for column_name, column_type in (
    ("recommended_action", "TEXT"),
    ("confidence", "NUMERIC"),
    ("signals_triggered", "INTEGER"),
    ("behavioral_match", "BOOLEAN"),
):
    cursor.execute(f"""
        ALTER TABLE fraud_alerts
        ADD COLUMN IF NOT EXISTS {column_name} {column_type}
    """)

cursor.execute("""
CREATE TABLE IF NOT EXISTS ml_features (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    num_devices INTEGER,
    num_ips INTEGER,
    total_requests INTEGER,
    events_per_minute INTEGER,
    anomaly_score INTEGER,
    ml_score INTEGER,
    timestamp TIMESTAMP
)
""")

for column_name, column_type in (
    ("events_per_minute", "INTEGER"),
    ("anomaly_score", "INTEGER"),
    ("ml_score", "INTEGER"),
):
    cursor.execute(f"""
        ALTER TABLE ml_features
        ADD COLUMN IF NOT EXISTS {column_name} {column_type}
    """)

conn.commit()

print("🚀 Consumer + Risk Engine Running")

# ==================================================
# NORMALIZER
# ==================================================

def normalize_event(event):
    return {
        "transaction_id": event.get("transaction_id", "N/A"),
        "user_id": event.get("user_id", "unknown_user"),
        "amount": float(event.get("amount", 0)),
        "location": event.get("location", "unknown"),
        "event_type": event.get("event_type", "unknown"),
        "device_type": event.get("device_type", "unknown"),
        "network": event.get("network", "NORMAL"),
        "ip": event.get("ip", "0.0.0.0"),
        "timestamp": event.get("timestamp")
    }


# ==================================================
# MAIN LOOP (FIXED LOGIC)
# ==================================================

for msg in consumer:

    try:
        raw_event = msg.value

        print(f"\n📥 RAW EVENT: {raw_event}")

        event = normalize_event(raw_event)

        print(f"✅ NORMALIZED EVENT: {event}")

        # ==========================================
        # SAVE EVENT
        # ==========================================

        cursor.execute("""
            INSERT INTO events (
                transaction_id,
                user_id,
                amount,
                location,
                event_type,
                device_type,
                network,
                ip,
                timestamp
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            event["transaction_id"],
            event["user_id"],
            event["amount"],
            event["location"],
            event["event_type"],
            event["device_type"],
            event["network"],
            event["ip"],
            event["timestamp"]
        ))

        conn.commit()

        print("✅ Event saved to PostgreSQL")

        # ==========================================
        # AI FRAUD INTELLIGENCE ENGINE
        # ==========================================

        result = analyze_event(event)

        print(f"🧠 Risk Result: {result}")

        # ==========================================
        # SAVE FRAUD ALERTS
        # ==========================================

        cursor.execute("""
            INSERT INTO fraud_alerts (
                user_id,
                reason,
                risk_level,
                risk_score,
                recommended_action,
                confidence,
                signals_triggered,
                behavioral_match,
                timestamp
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            result["user_id"],
            ", ".join(result["reasons"]),
            result["risk_level"],
            result["risk_score"],
            result["recommended_action"],
            result["confidence"],
            result["signals_triggered"],
            result["behavioral_match"],
            result["timestamp"]
        ))

        conn.commit()

        print("🚨 Fraud alert saved")

        intelligence = result.get("intelligence", {})
        profile = intelligence.get("profile", {})

        cursor.execute("""
            INSERT INTO ml_features (
                user_id,
                num_devices,
                num_ips,
                total_requests,
                events_per_minute,
                anomaly_score,
                ml_score,
                timestamp
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            result["user_id"],
            profile.get("known_devices", 0),
            profile.get("known_ips", 0),
            profile.get("history_events", 0),
            intelligence.get("events_per_minute", 0),
            intelligence.get("anomaly_score", 0),
            intelligence.get("ml_score", 0),
            result["timestamp"]
        ))

        conn.commit()

        print("🧬 ML features saved")

        # ======================================
        # SEND TO KAFKA
        # ======================================

        producer.send("fraud_alerts", result)

        # ======================================
        # SEND TO DASHBOARD
        # ======================================

        try:
            response = requests.post(
                "http://dashboard:8000/internal/fraud",
                json=result,
                timeout=5
            )

            print(f"📡 Dashboard Response: {response.status_code}")

        except Exception as dashboard_error:
            print(f"⚠️ Dashboard Error: {dashboard_error}")

    except Exception as e:
        print(f"❌ MAIN LOOP ERROR: {e}")

        try:
            conn.rollback()
        except:
            pass

        time.sleep(2)
