from datetime import datetime


BLACKLISTED_IPS = {"45.90.12.10", "203.45.11.90"}

RISKY_LOCATIONS = {
    "russia",
    "ukraine",
    "north korea",
    "iran",
    "afghanistan",
}

SUSPICIOUS_DEVICE_SCORES = {
    "unknown": 25,
    "emulator": 40,
    "rooted": 45,
    "jailbroken": 35,
}


def _event_hour(timestamp):
    if not timestamp:
        return None

    try:
        return datetime.fromisoformat(timestamp).hour
    except ValueError:
        return None


def get_risk_reasons(event, reason=None):
    reasons = []

    reason_text = (reason or "").strip().lower()
    if reason_text == "too many requests":
        reasons.append("Too many requests")
    elif reason_text == "multiple ips detected":
        reasons.append("Multiple IPs detected")
    elif reason_text == "multiple devices detected":
        reasons.append("Multiple devices detected")

    amount = float(event.get("amount", 0) or 0)
    if amount >= 500000:
        reasons.append("High transaction amount")
    elif amount >= 200000:
        reasons.append("Medium-high transaction amount")
    elif amount >= 50000:
        reasons.append("Moderate transaction amount")

    device = event.get("device_type", "").lower().strip()
    if any(pattern in device for pattern in SUSPICIOUS_DEVICE_SCORES):
        reasons.append("Suspicious device")

    ip = event.get("ip", "").strip()
    if ip in BLACKLISTED_IPS:
        reasons.append("Blacklisted IP")

    location = event.get("location", "").lower().strip()
    if location in RISKY_LOCATIONS:
        reasons.append("Foreign/risky location")

    network = event.get("network", "normal").lower().strip()
    if network == "vpn":
        reasons.append("VPN network")
    elif network == "tor":
        reasons.append("TOR network")

    hour = _event_hour(event.get("timestamp"))
    if hour is not None and (hour < 6 or hour > 22):
        reasons.append("Unusual login time")

    event_type = event.get("event_type", "").lower().strip()
    if "failed" in event_type:
        reasons.append("Multiple failed logins")
    elif event_type in {"password_reset", "password_change", "new_payee", "withdrawal"}:
        reasons.append("Sensitive account activity")

    return reasons or ["Normal behavior"]


def calculate_risk_score(event, reason=None):
    score = 0
    risk_signals = 0

    reason_text = (reason or "").strip().lower()
    if reason_text == "too many requests":
        score += 40
        risk_signals += 1
    elif reason_text == "multiple ips detected":
        score += 30
        risk_signals += 1
    elif reason_text == "multiple devices detected":
        score += 30
        risk_signals += 1

    amount = float(event.get("amount", 0) or 0)
    if amount >= 500000:
        score += 30
        risk_signals += 1
    elif amount >= 200000:
        score += 5
        risk_signals += 1
    elif amount >= 50000:
        score += 5
        risk_signals += 1

    device = event.get("device_type", "").lower().strip()
    for pattern, device_score in SUSPICIOUS_DEVICE_SCORES.items():
        if pattern in device:
            score += device_score
            risk_signals += 1
            break

    ip = event.get("ip", "").strip()
    if ip in BLACKLISTED_IPS:
        score += 35
        risk_signals += 1

    location = event.get("location", "").lower().strip()
    if location in RISKY_LOCATIONS:
        score += 10
        risk_signals += 1

    network = event.get("network", "normal").lower().strip()
    if network == "vpn":
        score += 10
        risk_signals += 1
    elif network == "tor":
        score += 25
        risk_signals += 1

    hour = _event_hour(event.get("timestamp"))
    if hour is not None and (hour < 6 or hour > 22):
        score += 20
        risk_signals += 1

    event_type = event.get("event_type", "").lower().strip()
    if "failed" in event_type:
        score += 25
        risk_signals += 1
    elif event_type in {"password_reset", "password_change", "new_payee", "withdrawal"}:
        score += 15
        risk_signals += 1

    if 3 <= risk_signals and score < 80:
        score += 10

    return min(score, 100)


def get_risk_level(score: int) -> str:
    if score >= 90:
        return "CRITICAL"
    if score >= 70:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    return "LOW"
