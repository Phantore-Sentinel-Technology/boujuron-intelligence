from datetime import datetime


# =========================
# CONFIGURATION (EASY TO SCALE)
# =========================

HIGH_RISK_COUNTRIES = {
    "russia": 40,
    "north korea": 50,
    "iran": 35,
    "afghanistan": 30
}

SUSPICIOUS_DEVICES = {
    "unknown device": 25,
    "emulator": 40,
    "rooted device": 45,
    "jailbroken iphone": 35
}

SUSPICIOUS_IPS = {
    "45.90.12.10": 35,
    "203.45.11.90": 30
}

TOR_NETWORK_SCORE = 60


# =========================
# CORE ENGINE
# =========================

def analyze_event(event):
    score = 0
    reasons = []

    # normalize input (VERY IMPORTANT in real systems)
    amount = float(event.get("amount", 0))
    location = event.get("location", "").lower().strip()
    device = event.get("device_type", "").lower().strip()
    ip = event.get("ip", "").strip()
    network = event.get("network", "").upper().strip()
    event_type = event.get("event_type", "").lower().strip()
    timestamp = event.get("timestamp")

    # =========================
    # 1. AMOUNT-BASED FRAUD
    # =========================

    if amount >= 2_000_000:
        score += 60
        reasons.append("Extremely large transaction")

    elif amount >= 1_000_000:
        score += 45
        reasons.append("Very large transaction")

    elif amount >= 500_000:
        score += 30
        reasons.append("Large transaction")

    elif amount >= 100_000:
        score += 15
        reasons.append("Moderate high-value transaction")

    # =========================
    # 2. COUNTRY RISK
    # =========================

    if location in HIGH_RISK_COUNTRIES:
        score += HIGH_RISK_COUNTRIES[location]
        reasons.append(f"High-risk country: {location}")

    # =========================
    # 3. DEVICE RISK
    # =========================

    if device in SUSPICIOUS_DEVICES:
        score += SUSPICIOUS_DEVICES[device]
        reasons.append(f"Suspicious device: {device}")

    # =========================
    # 4. IP RISK
    # =========================

    if ip in SUSPICIOUS_IPS:
        score += SUSPICIOUS_IPS[ip]
        reasons.append(f"Blacklisted IP: {ip}")

    # =========================
    # 5. NETWORK RISK (TOR / VPN)
    # =========================

    if network == "TOR":
        score += TOR_NETWORK_SCORE
        reasons.append("TOR network detected")

    elif network == "VPN":
        score += 25
        reasons.append("VPN usage detected")

    # =========================
    # 6. EVENT TYPE RISK
    # =========================

    if event_type == "multiple_failed_logins":
        score += 30
        reasons.append("Multiple failed login attempts")

    elif event_type == "password_reset":
        score += 10
        reasons.append("Password reset activity")

    # =========================
    # 7. TIME-BASED FRAUD (BEHAVIORAL)
    # =========================

    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp)
            hour = dt.hour

            if hour < 4:
                score += 25
                reasons.append("Unusual login time (late night)")

            elif hour < 6:
                score += 10
                reasons.append("Slightly unusual login time")

        except Exception:
            reasons.append("Invalid timestamp format")

    # =========================
    # 8. FINAL RISK CLASSIFICATION
    # =========================

    if score >= 90:
        risk_level = "CRITICAL"

    elif score >= 70:
        risk_level = "HIGH"

    elif score >= 40:
        risk_level = "MEDIUM"

    else:
        risk_level = "LOW"

    return {
        "risk_score": min(score, 100),  # cap at 100 for dashboard clarity
        "risk_level": risk_level,
        "reason": ", ".join(reasons) if reasons else "Normal activity"
    }