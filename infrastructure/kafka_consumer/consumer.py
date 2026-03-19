from config.settings import settings
from kafka import KafkaConsumer
import sqlite3
import json

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

# ✅ Create table
cursor.execute("""
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    event_type TEXT,
    device TEXT,
    ip TEXT,
    timestamp TEXT
)
""")
conn.commit()

print("Consumer started...")

# ✅ Process events
for message in consumer:
    event = message.value

    cursor.execute(
        """
        INSERT INTO events (user_id,event_type,device,ip,timestamp)
        VALUES (?,?,?,?,?)
        """,
        (
            event["user_id"],
            event["event_type"],
            event["device_type"],  # ⚠️ IMPORTANT FIX
            event["ip"],
            event["timestamp"]
        )
    )

    conn.commit()
    print("Stored event:", event)