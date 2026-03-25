from collections import defaultdict
from datetime import datetime, timedelta
from .scoring import calculate_risk_score

# Track user activity
user_events = defaultdict(list)


def is_fraud(event):
    user_id = event["user_id"]
    now = datetime.fromisoformat(event["timestamp"])

    user_events[user_id].append((now, event))

    user_events[user_id] = [
        (t, e) for t, e in user_events[user_id]
        if now - t <= timedelta(seconds=10)
    ]

    reason = None

    if len(user_events[user_id]) > 5:
        reason = "Too many requests"

    ips = {e["ip"] for _, e in user_events[user_id]}
    if len(ips) > 2:
        reason = "Multiple IPs detected"

    devices = {e["device_type"] for _, e in user_events[user_id]}
    if len(devices) > 2:
        reason = "Multiple devices detected"

    if reason:
        score = calculate_risk_score(event, reason)
        return True, reason, score

    return False, None, 0
