from confluent_kafka import Producer
import json

conf = {
    'bootstrap.servers': 'BOOTSTRAP_SERVER',
    'security.protocol': 'SASL_SSL',
    'sasl.mechanisms': 'PLAIN',
    'sasl.username': 'API_KEY',
    'sasl.password': 'API_SECRET'
}

producer = Producer(conf)

def send_event(event):

    producer.produce(
        "user_events",
        json.dumps(event).encode("utf-8")
    )
    producer.flush()