from config.settings import settings
from kafka import KafkaProducer
import json
import time

producer = None


def get_producer():
    global producer

    while producer is None:
        try:
            print("Connecting to Kafka...")
            producer = KafkaProducer(
                bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVER,
                value_serializer=lambda v: json.dumps(v).encode("utf-8")
            )
            print("Connected to Kafka ✅")
        except Exception as e:
            print("Kafka not ready, retrying in 5 seconds...")
            time.sleep(5)

    return producer


def send_event(event):
    kafka_producer = get_producer()
    kafka_producer.send(settings.KAFKA_TOPIC_EVENTS, event)
    kafka_producer.flush()
