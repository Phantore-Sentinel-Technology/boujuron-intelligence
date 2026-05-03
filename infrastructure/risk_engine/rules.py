from datetime import datetime


def check_rules(event, profile):
    reasons = []
    score = 0

    # New device
    if event["device_type"] not in profile["devices"]:
        reasons.append("New device")
        score += 20

    # New IP
    if event["ip"] not in profile["ips"]:
        reasons.append("New Ip address")
        score += 20

    # Old login time (Night activity)
    hour = datetime.fromisoformat(event["timestamp"]).hour
    if hour < 5 or hour > 23:
        reasons.append("Unusual login time")
        score += 15

    return score, reasons
