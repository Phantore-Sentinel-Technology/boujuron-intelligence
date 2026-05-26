def process_event(event):

    risk_score = 0
    reasons = []

    # =========================
    # DEVICE CHECK
    # =========================
    suspicious_devices = [
        "unknown_android",
        "emulator",
        "jailbroken_iphone"
    ]

    if event["device_type"] in suspicious_devices:
        risk_score += 40
        reasons.append("Suspicious device detected")

    # =========================
    # IP CHECK
    # =========================
    suspicious_ips = [
        "45.90.12.10",
        "203.45.11.90"
    ]

    if event["ip"] in suspicious_ips:
        risk_score += 35
        reasons.append("Suspicious IP address")

    # =========================
    # EVENT TYPE CHECK
    # =========================
    if event["event_type"] == "multiple_failed_logins":
        risk_score += 25
        reasons.append("Multiple failed logins")

    # =========================
    # DETERMINE RISK LEVEL
    # =========================
    if risk_score >= 70:
        level = "HIGH"

    elif risk_score >= 40:
        level = "MEDIUM"

    else:
        level = "LOW"

    return {
        "risk_score": risk_score,
        "risk_level": level,
        "reason": ", ".join(reasons) if reasons else "Normal activity"
    }