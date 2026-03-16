from config.settings import settings
from confluent_kafka import Producer
import json


conf = {
    "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVER
}

producer = Producer(conf)


def send_event(event):
    producer.produce(
        "user_events",
        json.dumps(event).encode("utf-8")
    )
    producer.flush()
