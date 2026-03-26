from kafka import KafkaConsumer
import json
import time
from config.settings import settings
from .notifier import send_alert

consumer = None

while consumer is None:
    try:
        print("Connecting to fraud topic...")
        consumer =