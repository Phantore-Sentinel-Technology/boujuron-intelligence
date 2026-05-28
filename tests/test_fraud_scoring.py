from infrastructure.fraud_detection.scoring import (
    calculate_risk_score,
    get_risk_level,
    get_risk_reasons,
)


def test_normal_login_stays_low():
    event = {
        "user_id": "normal_user",
        "event_type": "login",
        "device_type": "iphone",
        "ip": "8.8.8.8",
        "timestamp": "2026-05-28T12:00:00",
    }

    score = calculate_risk_score(event)

    assert score == 0
    assert get_risk_level(score) == "LOW"
    assert get_risk_reasons(event) == ["Normal behavior"]


def test_unknown_device_during_unusual_time_becomes_medium():
    event = {
        "user_id": "suspicious_user",
        "event_type": "login",
        "device_type": "unknown",
        "ip": "102.88.12.5",
        "timestamp": "2026-05-28T03:30:00",
    }

    score = calculate_risk_score(event)

    assert score == 45
    assert get_risk_level(score) == "MEDIUM"
    assert get_risk_reasons(event) == ["Suspicious device", "Unusual login time"]


def test_blacklisted_ip_pushes_suspicious_login_to_high():
    event = {
        "user_id": "fraud_user",
        "event_type": "login",
        "device_type": "unknown",
        "ip": "45.90.12.10",
        "timestamp": "2026-05-28T02:00:00",
    }

    score = calculate_risk_score(event)

    assert score == 80
    assert get_risk_level(score) == "HIGH"
    assert get_risk_reasons(event) == [
        "Suspicious device",
        "Blacklisted IP",
        "Unusual login time",
    ]


def test_critical_risk_level_starts_at_ninety():
    assert get_risk_level(39) == "LOW"
    assert get_risk_level(40) == "MEDIUM"
    assert get_risk_level(70) == "HIGH"
    assert get_risk_level(90) == "CRITICAL"
    assert get_risk_level(100) == "CRITICAL"


def test_combined_vpn_geo_ip_payload_scores_high_not_critical():
    event = {
        "user_id": "high_risk_user",
        "event_type": "login",
        "device_type": "unknown",
        "ip": "45.90.12.10",
        "location": "Russia",
        "network": "VPN",
        "amount": 250000,
        "timestamp": "2026-05-28T21:30:00",
    }

    score = calculate_risk_score(event)

    assert score == 85
    assert get_risk_level(score) == "HIGH"
    assert get_risk_reasons(event) == [
        "Medium-high transaction amount",
        "Suspicious device",
        "Blacklisted IP",
        "Foreign/risky location",
        "VPN network",
    ]


def test_sensitive_emulator_geo_payload_scores_high_not_medium():
    event = {
        "user_id": "high_risk_user_2",
        "event_type": "password_reset",
        "device_type": "emulator",
        "ip": "88.12.45.11",
        "location": "Ukraine",
        "network": "NORMAL",
        "amount": 80000,
        "timestamp": "2026-05-28T20:10:00",
    }

    score = calculate_risk_score(event)

    assert score == 80
    assert get_risk_level(score) == "HIGH"
    assert get_risk_reasons(event) == [
        "Moderate transaction amount",
        "Suspicious device",
        "Foreign/risky location",
        "Sensitive account activity",
    ]
