from confluent_kafka import Consumer
import json
import psycopg2

conf = {
    'bootstrap.servers': 'BOOTSTRAP_SERVER',
    'security.protocol': 'SASL_SSL',
    'sasl.mechanisms': 'PLAIN',
    'sasl.username': 'API_KEY',
    'sasl.password': 'API_SECRET',
    'group.id': 'phantore-group',
    'auto.offset.reset': 'earliest'
}

consumer = Consumer(conf)

consumer.subscribe(["user_events"])

conn = psycopg2.connect(
    "postgresql://USER:PASSWORD@HOST:5432/postgres"
)

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