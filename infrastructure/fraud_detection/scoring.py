from datetime import datetime


def calculate_risk_score(event, reason):
    score = 0

    # Base scoring
    if reason == "too many requests":
        score += 40
    elif reason == "multiple Ips detected":
        score += 30
    elif reason == "multiple device detected":
        score += 30

    # Time base risk
    hour = datetime.fromisoformat(event["timestamp"]).hour
    if hour < 6 or hour > 22:
        score += 20  # Suspicious hours

    # Device risk
    if event["device_type"].lower() == "unknown":
        score += 25

    # Normalize to 100
    return min(score, 100)


def get_risk_level(score: int) -> str:
    if score >= 85:
        return "HIGH"
    elif score >= 70:
        return "MEDIUM"
    return "LOW"
