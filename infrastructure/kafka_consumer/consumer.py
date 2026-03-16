from config.settings import settings
from confluent_kafka import Consumer
import psycopg2
import json

conf = {
    "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVER,
    "group.id": "phantore-group",
    "auto.offset.reset": "earliest"
}

consumer = Consumer(conf)
consumer.subscribe([settings.KAFKA_TOPIC_EVENTS])

conn = psycopg2.connect(settings.DATABASE_URL)
cursor = conn.cursor()

print("Consumer started...")

while True:
    msg = consumer.poll(1.0)
    if msg is None:
        continue

    event = json.loads(msg.value().decode())

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