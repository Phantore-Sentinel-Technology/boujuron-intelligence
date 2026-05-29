from datetime import datetime
from hashlib import sha256


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


def _stable_variation(event, low=-4, high=4):
    seed = "|".join([
        str(event.get("user_id", "")),
        str(event.get("event_type", "")),
        str(event.get("device_type", "")),
        str(event.get("ip", "")),
        str(event.get("timestamp", "")),
    ])
    span = high - low + 1
    return low + (int(sha256(seed.encode("utf-8")).hexdigest(), 16) % span)


def _calibrate_score(score, risk_signals, event):
    if risk_signals == 0:
        return 8 + _stable_variation(event, 0, 10)

    adjusted = score + _stable_variation(event)

    if score >= 90:
        return max(90, min(adjusted, 100))
    if score >= 70:
        return max(70, min(adjusted, 89))
    if score >= 40:
        return max(40, min(adjusted, 69))

    return max(1, min(adjusted, 39))


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

    return reasons or ["Known device and consistent login behavior"]


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

    return _calibrate_score(min(score, 100), risk_signals, event)


def get_risk_level(score: int) -> str:
    if score >= 90:
        return "CRITICAL"
    if score >= 70:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    return "LOW"


def get_recommended_action(risk_level: str) -> str:
    actions = {
        "LOW": "ALLOW",
        "MEDIUM": "STEP_UP_VERIFY",
        "HIGH": "BLOCK_AND_REVIEW",
        "CRITICAL": "FREEZE_AND_ESCALATE",
    }
    return actions.get(risk_level, "REVIEW")
