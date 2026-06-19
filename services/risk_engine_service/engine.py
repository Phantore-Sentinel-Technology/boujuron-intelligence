from datetime import datetime


HIGH_RISK_COUNTRIES = {
    "russia": 40,
    "north korea": 50,
    "iran": 35,
    "afghanistan": 30,
}

SUSPICIOUS_DEVICES = {
    "unknown device": 25,
    "emulator": 40,
    "rooted device": 45,
    "jailbroken iphone": 35,
}

SUSPICIOUS_IPS = {
    "45.90.12.10": 35,
    "203.45.11.90": 30,
}

TOR_NETWORK_SCORE = 60


def _signal(category, label, points, evidence):
    return {
        "category": category,
        "label": label,
        "points": points,
        "evidence": evidence,
    }


def _parse_timestamp(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def _action_for_level(level):
    return {
        "LOW": "ALLOW",
        "MEDIUM": "VERIFY",
        "HIGH": "BLOCK",
        "CRITICAL": "LOCK_ACCOUNT",
    }[level]


def _recommendation_for_level(level):
    return {
        "LOW": "ALLOW",
        "MEDIUM": "STEP_UP_VERIFICATION",
        "HIGH": "BLOCK_AND_REVIEW",
        "CRITICAL": "LOCK_ACCOUNT_AND_ESCALATE",
    }[level]


def analyze_event(event, behavior=None):
    behavior = behavior or {}
    risk_settings = behavior.get("settings", {})
    signals = []

    amount = float(event.get("amount") or 0)
    location = str(event.get("location") or "").lower().strip()
    device = str(event.get("device_type") or event.get("device") or "").lower().strip()
    device_id = str(event.get("device_id") or "").strip()
    ip = str(event.get("ip") or "").strip()
    network = str(event.get("network") or "").upper().strip()
    event_type = str(event.get("event_type") or "transaction").lower().strip()
    timestamp = _parse_timestamp(event.get("timestamp"))

    if amount >= 2_000_000:
        signals.append(_signal("TRANSACTION", "Extremely large transaction", 60, f"Amount {amount:.2f} is at least 2,000,000"))
    elif amount >= 1_000_000:
        signals.append(_signal("TRANSACTION", "Very large transaction", 45, f"Amount {amount:.2f} is at least 1,000,000"))
    elif amount >= 500_000:
        signals.append(_signal("TRANSACTION", "Large transaction", 30, f"Amount {amount:.2f} is at least 500,000"))
    elif amount >= 100_000:
        signals.append(_signal("TRANSACTION", "Moderate high-value transaction", 15, f"Amount {amount:.2f} is at least 100,000"))

    profile_ready = int(behavior.get("trusted_event_count") or 0) >= int(risk_settings.get("minimum_profile_events", 3))
    average_amount = float(behavior.get("average_amount") or 0)
    amount_multiplier = float(risk_settings.get("amount_spike_multiplier", 5))
    minimum_delta = float(risk_settings.get("minimum_amount_delta", 100_000))
    if profile_ready and average_amount > 0 and amount >= max(average_amount * amount_multiplier, average_amount + minimum_delta):
        multiplier = round(amount / average_amount, 1)
        signals.append(_signal("BEHAVIOR", "Transaction amount spike", 25, f"Amount is {multiplier}x the user's historical average"))

    if location in HIGH_RISK_COUNTRIES:
        signals.append(_signal("LOCATION", f"High-risk country: {location}", HIGH_RISK_COUNTRIES[location], f"{location.title()} is configured as a high-risk location"))

    known_locations = {str(item).lower().strip() for item in behavior.get("known_locations", []) if item}
    if profile_ready and location and known_locations and location not in known_locations:
        signals.append(_signal(
            "BEHAVIOR",
            "New transaction location",
            int(risk_settings.get("new_location_points", 20)),
            f"Location {location.title()} is not in the user's history",
        ))

    if device in SUSPICIOUS_DEVICES:
        signals.append(_signal("DEVICE", f"Suspicious device: {device}", SUSPICIOUS_DEVICES[device], f"Device type matched {device}"))

    if event.get("is_emulator") and device != "emulator":
        signals.append(_signal("DEVICE", "Emulator detected", 40, "Device telemetry indicates an emulator"))
    if event.get("is_rooted") and device != "rooted device":
        signals.append(_signal("DEVICE", "Rooted device detected", 45, "Device integrity checks indicate root access"))
    if event.get("browser_tampering"):
        signals.append(_signal("DEVICE", "Browser manipulation detected", 35, "Browser fingerprint or runtime integrity changed"))

    known_devices = {str(item).lower().strip() for item in behavior.get("known_devices", []) if item}
    device_identity = device_id.lower() or device
    if profile_ready and device_identity and known_devices and device_identity not in known_devices:
        signals.append(_signal(
            "BEHAVIOR",
            "New device",
            int(risk_settings.get("new_device_points", 25)),
            f"Device {device_id or device} has not been seen for this user",
        ))

    if ip in SUSPICIOUS_IPS:
        signals.append(_signal("NETWORK", f"Blacklisted IP: {ip}", SUSPICIOUS_IPS[ip], "IP address matched the configured blocklist"))

    if network == "TOR":
        signals.append(_signal("NETWORK", "TOR network detected", TOR_NETWORK_SCORE, "Connection is routed through TOR"))
    elif network == "VPN":
        signals.append(_signal("NETWORK", "VPN usage detected", 25, "Connection is routed through a VPN"))

    if event_type == "multiple_failed_logins":
        signals.append(_signal("ACCOUNT_TAKEOVER", "Multiple failed login attempts", 30, "Repeated authentication failures were reported"))
    elif event_type == "password_reset":
        signals.append(_signal("ACCOUNT_TAKEOVER", "Password reset activity", 10, "A password reset occurred during this activity"))

    failed_login_count = int(event.get("failed_login_count") or 0)
    if failed_login_count >= 5 and event_type != "multiple_failed_logins":
        signals.append(_signal("ACCOUNT_TAKEOVER", "Login velocity spike", 30, f"{failed_login_count} recent failed login attempts"))
    if event.get("password_changed_recently"):
        signals.append(_signal("ACCOUNT_TAKEOVER", "Recent password change", 20, "Password changed shortly before this event"))
    if event.get("sim_swap_detected"):
        signals.append(_signal("ACCOUNT_TAKEOVER", "SIM swap indicator", 50, "Mobile identity telemetry indicates a recent SIM change"))

    transaction_velocity = int(behavior.get("transaction_velocity") or 0)
    transaction_limit = int(risk_settings.get("transaction_velocity_limit", 5))
    login_velocity = int(behavior.get("login_velocity") or 0)
    login_limit = int(risk_settings.get("login_velocity_limit", 8))
    velocity_points = int(risk_settings.get("velocity_points", 30))
    velocity_minutes = int(risk_settings.get("velocity_window_minutes", 10))
    if event_type in {"transaction", "large_transfer", "transfer", "payment"} and transaction_velocity >= transaction_limit:
        signals.append(_signal(
            "VELOCITY",
            "Transaction velocity spike",
            velocity_points,
            f"{transaction_velocity + 1} transactions within {velocity_minutes} minutes",
        ))
    if event_type in {"login", "multiple_failed_logins"} and login_velocity >= login_limit:
        signals.append(_signal(
            "ACCOUNT_TAKEOVER",
            "Login velocity spike",
            velocity_points,
            f"{login_velocity + 1} login events within {velocity_minutes} minutes",
        ))

    if timestamp:
        hour = timestamp.hour
        usual_start = behavior.get("usual_hour_start")
        usual_end = behavior.get("usual_hour_end")
        if profile_ready and usual_start is not None and usual_end is not None and not int(usual_start) <= hour <= int(usual_end):
            signals.append(_signal(
                "BEHAVIOR",
                "Activity outside normal hours",
                int(risk_settings.get("unusual_hour_points", 20)),
                f"Activity at {hour:02d}:00 is outside the user's normal window",
            ))
        elif hour < 4:
            signals.append(_signal("BEHAVIOR", "Unusual login time (late night)", 25, f"Activity occurred at {hour:02d}:00"))
        elif hour < 6:
            signals.append(_signal("BEHAVIOR", "Slightly unusual login time", 10, f"Activity occurred at {hour:02d}:00"))

    score = min(sum(item["points"] for item in signals), 100)
    if score >= 90:
        risk_level = "CRITICAL"
    elif score >= 70:
        risk_level = "HIGH"
    elif score >= 40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    reasons = [item["label"] for item in signals]
    return {
        "risk_score": score,
        "risk_level": risk_level,
        "action": _action_for_level(risk_level),
        "recommendation": _recommendation_for_level(risk_level),
        "reason": ", ".join(reasons) if reasons else "Normal activity",
        "reasons": reasons,
        "signals": signals,
        "confidence": min(99, max(55, score + 4)),
        "behavioral_match": not any(item["category"] == "BEHAVIOR" for item in signals),
    }
