def detect_anomaly(event, profile):
    score = 0
    reasons = []

    # New device
    if event["device_type"] not in profile["devices"]:
        score += 30
        reasons.append("New device")

    # New IP
    if event["ip"] not in profile["ips"]:
        score += 30
        reasons.append("New IP")

    # High frequency spike
    if profile["total_requests"] > 20:
        score += 20
        reasons.append("High activity spike")

    return score, reasons
