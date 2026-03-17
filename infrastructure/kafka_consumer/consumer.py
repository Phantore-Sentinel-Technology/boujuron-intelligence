from config.settings import settings
from kafka import KafkaConsumer
import psycopg2
import json

consumer = KafkaConsumer(
    settings.KAFKA_TOPIC_EVENTS,
    bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVER,
    value_deserializer=lambda x: json.loads(x.decode("utf-8")),
    auto_offset_reset="earliest",
    group_id="phantore-group"
)

conn = psycopg2.connect(settings.DATABASE_URL)
cursor = conn.cursor()

print("Consumer started...")

for message in consumer:
    event = message.value

    cursor.execute(
        """
        INSERT INTO events (user_id,event_type,device,ip,timestamp)
        VALUES (%s,%s,%s,%s,%s)
        """,
        (
            event["user_id"],
            event["event_type"],
            event["device"],
            event["ip"],
            event["timestamp"]
        )
    )

    conn.commit()
    print("Stored event:", event)