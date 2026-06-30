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


def signal(category, label, points, evidence, strength="MEDIUM"):
    return {
        "category": category,
        "label": label,
        "points": points,
        "evidence": evidence,
        "strength": strength,
    }


def parse_timestamp(value):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def metadata(event):
    data = event.get("metadata")
    return data if isinstance(data, dict) else {}


def event_value(event, key, default=None):
    data = metadata(event)
    return event.get(key, data.get(key, default))


def event_flag(event, key):
    value = event_value(event, key, False)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return bool(value)


def event_int(event, key, default=0):
    try:
        return int(event_value(event, key, default) or 0)
    except (TypeError, ValueError):
        return default


def shared_transaction_signals(event, behavior):
    risk_settings = behavior.get("settings", {})
    signals = []
    location = str(event.get("location") or "").lower().strip()
    device = str(event.get("device_type") or event.get("device") or "").lower().strip()
    device_id = str(event.get("device_id") or "").strip()
    ip = str(event.get("ip") or "").strip()
    network = str(event.get("network") or "").upper().strip()
    event_type = str(event.get("event_type") or "transaction").lower().strip()
    timestamp = parse_timestamp(event.get("timestamp"))
    device_intelligence = behavior.get("device_intelligence") or {}
    takeover_context = behavior.get("account_takeover") or {}

    profile_ready = int(behavior.get("trusted_event_count") or 0) >= int(risk_settings.get("minimum_profile_events", 3))

    if location in HIGH_RISK_COUNTRIES:
        signals.append(signal("LOCATION", f"High-risk country: {location}", HIGH_RISK_COUNTRIES[location], f"{location.title()} is configured as a high-risk location", "STRONG"))

    known_locations = {str(item).lower().strip() for item in behavior.get("known_locations", []) if item}
    if profile_ready and location and known_locations and location not in known_locations:
        signals.append(signal("BEHAVIOR", "New transaction location", int(risk_settings.get("new_location_points", 20)), f"Location {location.title()} is not in the user's history"))

    if device in SUSPICIOUS_DEVICES:
        signals.append(signal("DEVICE", f"Suspicious device: {device}", SUSPICIOUS_DEVICES[device], f"Device type matched {device}", "STRONG"))

    if event_flag(event, "is_emulator") and device != "emulator":
        signals.append(signal("DEVICE", "Emulator detected", 40, "Device telemetry indicates an emulator", "STRONG"))
    if event_flag(event, "is_rooted") and device != "rooted device":
        signals.append(signal("DEVICE", "Rooted device detected", 45, "Device integrity checks indicate root access", "STRONG"))
    if event_flag(event, "browser_tampering"):
        signals.append(signal("DEVICE", "Browser manipulation detected", 35, "Browser fingerprint or runtime integrity changed", "STRONG"))
    if str(event_value(event, "device_attestation") or "").upper() in {"FAILED", "INVALID", "UNTRUSTED"}:
        signals.append(signal("DEVICE", "Device attestation failed", 45, "Client device integrity proof could not be trusted", "STRONG"))

    device_status = str(device_intelligence.get("status") or "").upper()
    if device_status == "BLOCKED":
        signals.append(signal("DEVICE", "Blocked device fingerprint", 80, "This device fingerprint was previously blocked", "CRITICAL"))
    elif device_status == "SUSPICIOUS":
        signals.append(signal("DEVICE", "Suspicious device fingerprint", 35, "This device fingerprint has prior high-risk activity", "STRONG"))

    known_devices = {str(item).lower().strip() for item in behavior.get("known_devices", []) if item}
    device_identity = device_id.lower() or device
    if device_intelligence.get("is_new_device") and profile_ready:
        signals.append(signal("BEHAVIOR", "New device", int(risk_settings.get("new_device_points", 25)), f"Fingerprint {device_intelligence.get('fingerprint', '')[:12]} has not been seen for this user"))
    elif profile_ready and device_identity and known_devices and device_identity not in known_devices:
        signals.append(signal("BEHAVIOR", "New device", int(risk_settings.get("new_device_points", 25)), f"Device {device_id or device} has not been seen for this user"))

    if ip in SUSPICIOUS_IPS:
        signals.append(signal("NETWORK", f"Blacklisted IP: {ip}", SUSPICIOUS_IPS[ip], "IP address matched the configured blocklist", "STRONG"))

    if network == "TOR":
        signals.append(signal("NETWORK", "TOR network detected", TOR_NETWORK_SCORE, "Connection is routed through TOR", "CRITICAL"))
    elif network in {"VPN", "PROXY"}:
        signals.append(signal("NETWORK", f"{network} usage detected", 25, f"Connection is routed through a {network}"))

    failed_login_count = event_int(event, "failed_login_count")
    if event_type in {"multiple_failed_logins", "login_failure"}:
        signals.append(signal("ACCOUNT_TAKEOVER", "Multiple failed login attempts", 30, "Repeated authentication failures were reported"))
    if failed_login_count >= 5 and event_type != "multiple_failed_logins":
        signals.append(signal("ACCOUNT_TAKEOVER", "Login velocity spike", 30, f"{failed_login_count} recent failed login attempts"))
    if event_flag(event, "password_changed_recently"):
        signals.append(signal("ACCOUNT_TAKEOVER", "Recent password change", 20, "Password changed shortly before this event"))
    if event_flag(event, "sim_swap_detected"):
        signals.append(signal("ACCOUNT_TAKEOVER", "SIM swap indicator", 50, "Mobile identity telemetry indicates a recent SIM change", "STRONG"))
    if device_intelligence.get("is_new_device") and event_flag(event, "password_changed_recently"):
        signals.append(signal("ACCOUNT_TAKEOVER", "New device after password reset", 35, "A new device appeared shortly after password reset activity", "STRONG"))
    if device_intelligence.get("is_new_device") and event_flag(event, "sim_swap_detected"):
        signals.append(signal("ACCOUNT_TAKEOVER", "New device after SIM change", 45, "A new device appeared shortly after mobile identity changed", "STRONG"))

    registration_count = event_int(event, "registration_count")
    accounts_from_ip = event_int(event, "accounts_from_ip")
    accounts_from_device = event_int(event, "accounts_from_device")
    automation_score = event_int(event, "automation_score")
    if event_type in {"bot_attack", "credential_stuffing"}:
        signals.append(signal("BOT", "Credential stuffing pattern", 50, "Authentication telemetry matches automated credential testing", "STRONG"))
    if failed_login_count >= 20:
        signals.append(signal("BOT", "Repeated failed attempts", 35, f"{failed_login_count} failed attempts indicate automation", "STRONG"))
    if accounts_from_ip >= 10:
        signals.append(signal("BOT", "Many accounts from one IP", 35, f"{accounts_from_ip} accounts share the same network source", "STRONG"))
    if accounts_from_device >= 5:
        signals.append(signal("BOT", "Many accounts from one device", 40, f"{accounts_from_device} accounts share one device fingerprint", "STRONG"))
    if registration_count >= 5:
        signals.append(signal("BOT", "Registration velocity spike", 35, f"{registration_count} registrations originated from the same identity cluster"))
    if automation_score >= 80:
        signals.append(signal("BOT", "Automation-like timing", 30, f"Interaction cadence produced automation score {automation_score}"))

    if event_flag(event, "mule_account_suspected"):
        signals.append(signal("NETWORK", "Mule account movement", 45, "Funds movement pattern resembles mule-account pass-through behavior", "STRONG"))

    transaction_velocity = int(behavior.get("transaction_velocity") or 0)
    transaction_limit = int(risk_settings.get("transaction_velocity_limit", 5))
    login_velocity = int(behavior.get("login_velocity") or 0)
    login_limit = int(risk_settings.get("login_velocity_limit", 8))
    velocity_points = int(risk_settings.get("velocity_points", 30))
    velocity_minutes = int(risk_settings.get("velocity_window_minutes", 10))
    if event_type in {"transaction", "large_transfer", "transfer", "payment", "wallet_transfer", "agent_cashout", "pos_withdrawal", "debit"} and transaction_velocity >= transaction_limit:
        signals.append(signal("VELOCITY", "Transaction velocity spike", velocity_points, f"{transaction_velocity + 1} transactions within {velocity_minutes} minutes", "STRONG"))
    if event_type in {"login", "login_success", "login_failure", "multiple_failed_logins"} and login_velocity >= login_limit:
        signals.append(signal("ACCOUNT_TAKEOVER", "Login velocity spike", velocity_points, f"{login_velocity + 1} login events within {velocity_minutes} minutes"))

    if timestamp:
        hour = timestamp.hour
        usual_start = behavior.get("usual_hour_start")
        usual_end = behavior.get("usual_hour_end")
        if profile_ready and usual_start is not None and usual_end is not None and not int(usual_start) <= hour <= int(usual_end):
            signals.append(signal("BEHAVIOR", "Activity outside normal hours", int(risk_settings.get("unusual_hour_points", 20)), f"Activity at {hour:02d}:00 is outside the user's normal window"))
        elif hour < 4:
            signals.append(signal("BEHAVIOR", "Unusual transaction time (late night)", 25, f"Activity occurred at {hour:02d}:00"))
        elif hour < 6:
            signals.append(signal("BEHAVIOR", "Slightly unusual transaction time", 10, f"Activity occurred at {hour:02d}:00", "WEAK"))

    signals.extend(takeover_context.get("signals") or [])
    return signals


def calculate_confidence(score, signals, profile_ready=False):
    if not signals:
        return 92
    strong_count = sum(1 for item in signals if item.get("strength") in {"STRONG", "CRITICAL"} or item["points"] >= 35)
    weak_count = sum(1 for item in signals if item.get("strength") == "WEAK" or item["points"] <= 15)
    categories = {item["category"] for item in signals}
    confidence = 45 + min(score, 70) * 0.35 + strong_count * 7 + max(0, len(categories) - 1) * 4
    if not profile_ready:
        confidence -= 8
    if len(signals) == 1:
        confidence -= 14
    confidence -= weak_count * 4
    return int(max(35, min(99, round(confidence))))


def level_from_score(score):
    if score >= 90:
        return "CRITICAL"
    if score >= 70:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    return "LOW"


def level_from_evidence(score, signals):
    if score < 40:
        return "LOW"
    if score < 70:
        return "MEDIUM"
    if score < 90:
        return "HIGH"

    strong_count = sum(
        1 for item in signals
        if item.get("strength") in {"STRONG", "CRITICAL"} or item["points"] >= 35
    )
    critical_count = sum(1 for item in signals if item.get("strength") == "CRITICAL")
    categories = {item["category"] for item in signals}
    has_extreme_pattern = (
        (critical_count >= 1 and strong_count >= 2)
        or strong_count >= 3
        or (score >= 98 and len(categories) >= 2)
    )
    return "CRITICAL" if has_extreme_pattern else "HIGH"


def action_for_decision(level, confidence):
    if level == "CRITICAL":
        return "PND_OR_BLOCK"
    if level == "HIGH":
        return "HOLD_FOR_REVIEW"
    if level == "MEDIUM":
        return "STEP_UP_VERIFY"
    return "ALLOW"
