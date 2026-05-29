from infrastructure.fraud_detection import ai_engine


def setup_function():
    ai_engine.user_profiles.clear()
    ai_engine.feature_history.clear()
    ai_engine.ml_model = None


def make_event(user_id, timestamp, **overrides):
    event = {
        "user_id": user_id,
        "transaction_id": "N/A",
        "amount": 10000,
        "location": "lagos",
        "event_type": "login",
        "device_type": "iphone",
        "ip": "102.88.12.5",
        "timestamp": timestamp,
    }
    event.update(overrides)
    return event


def test_ai_engine_keeps_rule_based_result_compatible():
    event = make_event(
        "fraud_user",
        "2026-05-28T02:00:00",
        device_type="unknown",
        ip="45.90.12.10",
    )

    result = ai_engine.analyze_event(event)

    assert 70 <= result["risk_score"] <= 89
    assert result["risk_level"] == "HIGH"
    assert result["recommended_action"] == "BLOCK_AND_REVIEW"
    assert 0.0 < result["confidence"] <= 1.0
    assert "Blacklisted IP" in result["reasons"]
    assert "intelligence" in result


def test_velocity_detection_scores_rapid_user_activity():
    result = None

    for second in range(5):
        result = ai_engine.analyze_event(
            make_event("fast_user", f"2026-05-28T12:00:0{second}")
        )

    assert result["intelligence"]["events_per_minute"] == 5
    assert result["intelligence"]["velocity_score"] == 50
    assert "Elevated event velocity" in result["reasons"]


def test_velocity_detection_can_escalate_spam_to_critical():
    result = None

    for second in range(10):
        result = ai_engine.analyze_event(
            make_event(
                "spam_user",
                f"2026-05-28T12:00:{second:02d}",
                event_type="failed_login",
            )
        )

    assert 90 <= result["risk_score"] <= 100
    assert result["risk_level"] == "CRITICAL"
    assert result["recommended_action"] == "FREEZE_AND_ESCALATE"
    assert result["intelligence"]["velocity_score"] == 50
    assert "High event velocity" in result["reasons"]


def test_user_history_anomaly_detects_profile_change():
    for day in range(1, 4):
        ai_engine.analyze_event(
            make_event("profile_user", f"2026-05-2{day}T12:00:00")
        )

    result = ai_engine.analyze_event(
        make_event(
            "profile_user",
            "2026-05-28T18:00:00",
            amount=250000,
            location="russia",
            device_type="android_emulator",
            ip="203.45.11.90",
        )
    )

    assert result["intelligence"]["anomaly_score"] >= 50
    assert "User anomaly: new device" in result["reasons"]
    assert "User anomaly: new IP" in result["reasons"]
    assert "Behavioral fingerprint mismatch" in result["reasons"]


def test_recent_high_risk_event_decays_into_later_score():
    ai_engine.analyze_event(
        make_event(
            "decay_user",
            "2026-05-28T02:00:00",
            device_type="unknown",
            ip="45.90.12.10",
        )
    )

    result = ai_engine.analyze_event(
        make_event("decay_user", "2026-05-28T03:00:00")
    )

    assert result["intelligence"]["risk_decay_score"] > 0
    assert "Residual risk from recent activity" in result["reasons"]


def test_high_risk_vpn_geo_payload_stays_high_for_new_user():
    result = ai_engine.analyze_event(
        make_event(
            "high_risk_user",
            "2026-05-28T21:30:00",
            event_type="login",
            device_type="unknown",
            ip="45.90.12.10",
            location="Russia",
            network="VPN",
            amount=250000,
        )
    )

    assert 80 <= result["risk_score"] <= 89
    assert result["risk_level"] == "HIGH"
    assert result["recommended_action"] == "BLOCK_AND_REVIEW"
    assert result["signals_triggered"] >= 5
    assert "VPN network" in result["reasons"]
    assert "Foreign/risky location" in result["reasons"]


def test_high_risk_sensitive_emulator_payload_stays_high_for_new_user():
    result = ai_engine.analyze_event(
        make_event(
            "high_risk_user_2",
            "2026-05-28T20:10:00",
            event_type="password_reset",
            device_type="emulator",
            ip="88.12.45.11",
            location="Ukraine",
            network="NORMAL",
            amount=80000,
        )
    )

    assert 70 <= result["risk_score"] <= 89
    assert result["risk_level"] == "HIGH"
    assert result["recommended_action"] == "BLOCK_AND_REVIEW"
    assert result["signals_triggered"] >= 4
    assert "Sensitive account activity" in result["reasons"]
    assert "Foreign/risky location" in result["reasons"]
