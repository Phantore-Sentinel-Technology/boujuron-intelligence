from collections import defaultdict
from datetime import datetime, timedelta

# Track user activity
user_events = defaultdict(list)


def is_fraud(event):
    user_id = event["user_id"]
    now = datetime.fromisoformat(event["timestamp"])

    user_events[user_id].append((now, event))

    # Keep only last 10 seconds
    user_events[user_id] = [
        (t, e) for t, e in user_events[user_id]
        if now - t <= timedelta(seconds=10)
    ]

    # For Too many events
    if len(user_events[user_id]) > 5:
        return True, "Too many requests"

    # For Multiple IPs
    ips = {e["ip"] for _, e in user_events[user_id]}
    if len(ips) > 2:
        return True, "Multiple IPs detected"

    # For Multiple devices
    devices = {e["device_type"] for _, e in user_events[user_id]}
    if len(devices) > 2:
        return True, "Multiple devices detected"

    return False, None
