from datetime import datetime


def check_rules(event, profile):
    reasons = []
    score = 0

    # =========================
    # NEW DEVICE
    # =========================
    if event["device_type"] not in profile["known_devices"]:
        score += 25
        reasons.append("New device detected")

    # =========================
    # NEW IP
    # =========================
    if event["ip"] not in profile["known_ips"]:
        score += 25
        reasons.append("New IP detected")

    # =========================
    # TOO MANY REQUESTS
    # =========================
    if profile["total_requests"] > 10:
        score += 30
        reasons.append("High request frequency")

    # =========================
    # SUSPICIOUS LOGIN TIME
    # =========================
    hour = datetime.fromisoformat(event["timestamp"]).hour

    if hour < 5:
        score += 20
        reasons.append("Suspicious login time")

    return score, reasons