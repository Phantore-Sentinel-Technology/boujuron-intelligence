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