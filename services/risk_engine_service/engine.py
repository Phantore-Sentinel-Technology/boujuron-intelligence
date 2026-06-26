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


def _metadata(event):
    data = event.get("metadata")
    return data if isinstance(data, dict) else {}


def _event_value(event, key, default=None):
    data = _metadata(event)
    return event.get(key, data.get(key, default))


def _event_flag(event, key):
    value = _event_value(event, key, False)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def _event_int(event, key, default=0):
    try:
        return int(_event_value(event, key, default) or 0)
    except (TypeError, ValueError):
        return default


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
    device_intelligence = behavior.get("device_intelligence") or {}
    takeover_context = behavior.get("account_takeover") or {}

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

    if _event_flag(event, "is_emulator") and device != "emulator":
        signals.append(_signal("DEVICE", "Emulator detected", 40, "Device telemetry indicates an emulator"))
    if _event_flag(event, "is_rooted") and device != "rooted device":
        signals.append(_signal("DEVICE", "Rooted device detected", 45, "Device integrity checks indicate root access"))
    if _event_flag(event, "browser_tampering"):
        signals.append(_signal("DEVICE", "Browser manipulation detected", 35, "Browser fingerprint or runtime integrity changed"))
    if str(_event_value(event, "device_attestation") or "").upper() in {"FAILED", "INVALID", "UNTRUSTED"}:
        signals.append(_signal("DEVICE", "Device attestation failed", 45, "Client device integrity proof could not be trusted"))

    device_status = str(device_intelligence.get("status") or "").upper()
    if device_status == "BLOCKED":
        signals.append(_signal("DEVICE", "Blocked device fingerprint", 80, "This device fingerprint was previously blocked"))
    elif device_status == "SUSPICIOUS":
        signals.append(_signal("DEVICE", "Suspicious device fingerprint", 35, "This device fingerprint has prior high-risk activity"))

    known_devices = {str(item).lower().strip() for item in behavior.get("known_devices", []) if item}
    device_identity = device_id.lower() or device
    if device_intelligence.get("is_new_device") and profile_ready:
        signals.append(_signal(
            "BEHAVIOR",
            "New device",
            int(risk_settings.get("new_device_points", 25)),
            f"Fingerprint {device_intelligence.get('fingerprint', '')[:12]} has not been seen for this user",
        ))
    elif profile_ready and device_identity and known_devices and device_identity not in known_devices:
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
    elif network in {"VPN", "PROXY"}:
        signals.append(_signal("NETWORK", f"{network} usage detected", 25, f"Connection is routed through a {network}"))

    if event_type in {"multiple_failed_logins", "login_failure"}:
        signals.append(_signal("ACCOUNT_TAKEOVER", "Multiple failed login attempts", 30, "Repeated authentication failures were reported"))
    elif event_type in {"password_reset", "password_change"}:
        signals.append(_signal("ACCOUNT_TAKEOVER", "Password reset activity", 10, "A password reset occurred during this activity"))
    elif event_type == "sim_swap":
        signals.append(_signal("ACCOUNT_TAKEOVER", "SIM swap indicator", 50, "Mobile identity telemetry indicates a recent SIM change"))

    failed_login_count = _event_int(event, "failed_login_count")
    if failed_login_count >= 5 and event_type != "multiple_failed_logins":
        signals.append(_signal("ACCOUNT_TAKEOVER", "Login velocity spike", 30, f"{failed_login_count} recent failed login attempts"))
    if _event_flag(event, "password_changed_recently"):
        signals.append(_signal("ACCOUNT_TAKEOVER", "Recent password change", 20, "Password changed shortly before this event"))
    if _event_flag(event, "sim_swap_detected") and event_type != "sim_swap":
        signals.append(_signal("ACCOUNT_TAKEOVER", "SIM swap indicator", 50, "Mobile identity telemetry indicates a recent SIM change"))
    if device_intelligence.get("is_new_device") and _event_flag(event, "password_changed_recently"):
        signals.append(_signal("ACCOUNT_TAKEOVER", "New device after password reset", 35, "A new device appeared shortly after password reset activity"))
    if device_intelligence.get("is_new_device") and _event_flag(event, "sim_swap_detected"):
        signals.append(_signal("ACCOUNT_TAKEOVER", "New device after SIM change", 45, "A new device appeared shortly after mobile identity changed"))
    if _event_flag(event, "new_beneficiary_added"):
        signals.append(_signal("ACCOUNT_TAKEOVER", "New beneficiary before transfer", 25, "A new beneficiary was added before this value movement"))
    signals.extend(takeover_context.get("signals") or [])

    registration_count = _event_int(event, "registration_count")
    accounts_from_ip = _event_int(event, "accounts_from_ip")
    accounts_from_device = _event_int(event, "accounts_from_device")
    automation_score = _event_int(event, "automation_score")
    if event_type in {"bot_attack", "credential_stuffing"}:
        signals.append(_signal("BOT", "Credential stuffing pattern", 50, "Authentication telemetry matches automated credential testing"))
    if failed_login_count >= 20:
        signals.append(_signal("BOT", "Repeated failed attempts", 35, f"{failed_login_count} failed attempts indicate automation"))
    if accounts_from_ip >= 10:
        signals.append(_signal("BOT", "Many accounts from one IP", 35, f"{accounts_from_ip} accounts share the same network source"))
    if accounts_from_device >= 5:
        signals.append(_signal("BOT", "Many accounts from one device", 40, f"{accounts_from_device} accounts share one device fingerprint"))
    if registration_count >= 5:
        signals.append(_signal("BOT", "Registration velocity spike", 35, f"{registration_count} registrations originated from the same identity cluster"))
    if automation_score >= 80:
        signals.append(_signal("BOT", "Automation-like timing", 30, f"Interaction cadence produced automation score {automation_score}"))

    if event_type in {"airtime_purchase", "data_purchase"} and amount >= 50_000:
        signals.append(_signal("TRANSACTION", "Airtime/data purchase abuse", 25, "Airtime or data purchase volume is unusually high for wallet activity"))
    if event_type in {"pos_withdrawal", "agent_cashout"} and amount >= 300_000:
        signals.append(_signal("TRANSACTION", "POS/agent transaction anomaly", 30, "High-value agent or POS movement requires review"))
    if _event_flag(event, "mule_account_suspected"):
        signals.append(_signal("NETWORK", "Mule account movement", 45, "Funds movement pattern resembles mule-account pass-through behavior"))

    transaction_velocity = int(behavior.get("transaction_velocity") or 0)
    transaction_limit = int(risk_settings.get("transaction_velocity_limit", 5))
    login_velocity = int(behavior.get("login_velocity") or 0)
    login_limit = int(risk_settings.get("login_velocity_limit", 8))
    velocity_points = int(risk_settings.get("velocity_points", 30))
    velocity_minutes = int(risk_settings.get("velocity_window_minutes", 10))
    if event_type in {"transaction", "large_transfer", "transfer", "payment", "wallet_transfer", "agent_cashout", "pos_withdrawal"} and transaction_velocity >= transaction_limit:
        signals.append(_signal(
            "VELOCITY",
            "Transaction velocity spike",
            velocity_points,
            f"{transaction_velocity + 1} transactions within {velocity_minutes} minutes",
        ))
    if event_type in {"login", "login_success", "login_failure", "multiple_failed_logins"} and login_velocity >= login_limit:
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
    takeover_signals = [item for item in signals if item["category"] == "ACCOUNT_TAKEOVER"]
    takeover_score = min(sum(item["points"] for item in takeover_signals), 100)
    if takeover_score >= 70:
        takeover_level = "CRITICAL"
        takeover_recommendation = "LOCK_ACCOUNT"
    elif takeover_score >= 40:
        takeover_level = "HIGH"
        takeover_recommendation = "BLOCK_AND_VERIFY"
    elif takeover_score > 0:
        takeover_level = "MEDIUM"
        takeover_recommendation = "STEP_UP_VERIFICATION"
    else:
        takeover_level = "LOW"
        takeover_recommendation = "ALLOW"
    action = _action_for_level(risk_level)
    recommendation = _recommendation_for_level(risk_level)
    if takeover_score >= 70:
        action = "LOCK_ACCOUNT"
        recommendation = "LOCK_ACCOUNT_AND_ESCALATE"
    return {
        "risk_score": score,
        "risk_level": risk_level,
        "action": action,
        "recommendation": recommendation,
        "reason": ", ".join(reasons) if reasons else "Normal activity",
        "reasons": reasons,
        "signals": signals,
        "confidence": min(99, max(55, score + 4)),
        "behavioral_match": not any(item["category"] == "BEHAVIOR" for item in signals),
        "account_takeover": {
            "detected": takeover_score >= 70,
            "score": takeover_score,
            "level": takeover_level,
            "recommendation": takeover_recommendation,
            "indicators": [item["label"] for item in takeover_signals],
        },
    }
