from datetime import datetime


BLACKLISTED_IPS = {"45.90.12.10", "203.45.11.90"}

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

    device = event.get("device_type", "").lower().strip()
    if any(pattern in device for pattern in SUSPICIOUS_DEVICE_SCORES):
        reasons.append("Suspicious device")

    ip = event.get("ip", "").strip()
    if ip in BLACKLISTED_IPS:
        reasons.append("Blacklisted IP")

    hour = _event_hour(event.get("timestamp"))
    if hour is not None and (hour < 6 or hour > 22):
        reasons.append("Unusual login time")

    event_type = event.get("event_type", "").lower().strip()
    if "failed" in event_type:
        reasons.append("Multiple failed logins")

    return reasons or ["Normal behavior"]


def calculate_risk_score(event, reason=None):
    score = 0

    reason_text = (reason or "").strip().lower()
    if reason_text == "too many requests":
        score += 40
    elif reason_text == "multiple ips detected":
        score += 30
    elif reason_text == "multiple devices detected":
        score += 30

    amount = float(event.get("amount", 0) or 0)
    if amount >= 500000:
        score += 30

    device = event.get("device_type", "").lower().strip()
    for pattern, device_score in SUSPICIOUS_DEVICE_SCORES.items():
        if pattern in device:
            score += device_score
            break

    ip = event.get("ip", "").strip()
    if ip in BLACKLISTED_IPS:
        score += 35

    hour = _event_hour(event.get("timestamp"))
    if hour is not None and (hour < 6 or hour > 22):
        score += 20

    event_type = event.get("event_type", "").lower().strip()
    if "failed" in event_type:
        score += 25

    return min(score, 100)


def get_risk_level(score: int) -> str:
    if score >= 70:
        return "HIGH"
    if score >= 30:
        return "MEDIUM"
    return "LOW"
