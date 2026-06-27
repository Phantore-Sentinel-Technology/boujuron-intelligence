from services.risk_engine_service.engine import analyze_event


def test_normal_transaction_is_allowed():
    result = analyze_event({
        "user_id": "acct_normal",
        "amount": 12_000,
        "device": "iphone 15",
        "ip": "102.88.45.21",
        "location": "nigeria",
        "network": "MOBILE",
        "event_type": "transaction",
        "timestamp": "2026-06-19T12:00:00",
    })

    assert result["risk_score"] == 0
    assert result["risk_level"] == "LOW"
    assert result["action"] == "ALLOW"
    assert result["signals"] == []


def test_behavioral_amount_spike_adds_explainable_signal():
    result = analyze_event(
        {
            "user_id": "acct_spike",
            "amount": 250_000,
            "device": "iphone 15",
            "ip": "102.88.45.22",
            "location": "nigeria",
            "network": "MOBILE",
            "timestamp": "2026-06-19T12:00:00",
        },
        {
            "trusted_event_count": 10,
            "average_amount": 20_000,
            "known_devices": ["iphone 15"],
            "known_locations": ["nigeria"],
        },
    )

    labels = [signal["label"] for signal in result["signals"]]
    assert "Transaction amount spike" in labels
    assert result["risk_level"] == "MEDIUM"
    assert result["action"] == "VERIFY"
    assert result["recommendation"] == "STEP_UP_VERIFICATION"


def test_rooted_new_device_and_vpn_is_critical():
    result = analyze_event(
        {
            "user_id": "acct_device",
            "amount": 20_000,
            "device": "android",
            "device_id": "new-device-2",
            "is_rooted": True,
            "ip": "102.88.45.23",
            "location": "nigeria",
            "network": "VPN",
            "timestamp": "2026-06-19T12:00:00",
        },
        {
            "trusted_event_count": 10,
            "known_devices": ["old-device-1"],
            "known_locations": ["nigeria"],
        },
    )

    assert result["risk_score"] >= 70
    assert result["risk_level"] == "CRITICAL"
    assert result["action"] == "LOCK_ACCOUNT"
    assert result["recommendation"] == "AUTO_PND_FREEZE_ACCOUNT_AND_ESCALATE"


def test_account_takeover_signals_lock_account():
    result = analyze_event({
        "user_id": "acct_ato",
        "amount": 0,
        "device": "android",
        "ip": "102.88.45.24",
        "location": "nigeria",
        "network": "MOBILE",
        "event_type": "login",
        "failed_login_count": 8,
        "password_changed_recently": True,
        "sim_swap_detected": True,
        "timestamp": "2026-06-19T12:00:00",
    })

    assert result["risk_score"] == 100
    assert result["risk_level"] == "CRITICAL"
    assert result["action"] == "LOCK_ACCOUNT"
    assert result["recommendation"] == "AUTO_PND_FREEZE_ACCOUNT_AND_ESCALATE"


def test_organization_policy_controls_behavioral_signal_points():
    result = analyze_event(
        {
            "user_id": "acct_policy",
            "amount": 20_000,
            "device_id": "new-device",
            "device": "android",
            "ip": "102.88.45.25",
            "location": "kenya",
            "timestamp": "2026-06-19T12:00:00",
        },
        {
            "trusted_event_count": 10,
            "average_amount": 15_000,
            "known_devices": ["trusted-device"],
            "known_locations": ["nigeria"],
            "settings": {
                "minimum_profile_events": 3,
                "new_device_points": 35,
                "new_location_points": 30,
            },
        },
    )

    points = {signal["label"]: signal["points"] for signal in result["signals"]}
    assert points["New device"] == 35
    assert points["New transaction location"] == 30


def test_transaction_velocity_window_adds_risk():
    result = analyze_event(
        {
            "user_id": "acct_velocity",
            "amount": 5_000,
            "device": "iphone",
            "ip": "102.88.45.26",
            "location": "nigeria",
            "event_type": "transaction",
            "timestamp": "2026-06-19T12:00:00",
        },
        {
            "trusted_event_count": 6,
            "transaction_velocity": 5,
            "settings": {
                "minimum_profile_events": 3,
                "transaction_velocity_limit": 5,
                "velocity_window_minutes": 10,
                "velocity_points": 40,
            },
        },
    )

    assert "Transaction velocity spike" in result["reasons"]
    assert result["risk_level"] == "MEDIUM"
    assert result["action"] == "VERIFY"


def test_failed_device_attestation_is_high_risk():
    result = analyze_event({
        "user_id": "acct_attestation",
        "amount": 5_000,
        "device": "android",
        "device_attestation": "FAILED",
        "ip": "102.88.45.27",
        "location": "nigeria",
        "event_type": "login",
        "timestamp": "2026-06-19T12:00:00",
    })

    assert "Device attestation failed" in result["reasons"]
    assert result["risk_level"] == "MEDIUM"


def test_blocked_fingerprint_is_locked_immediately():
    result = analyze_event(
        {
            "user_id": "acct_blocked_device",
            "amount": 0,
            "device": "iphone",
            "ip": "102.88.45.28",
            "location": "nigeria",
            "event_type": "login",
            "timestamp": "2026-06-19T12:00:00",
        },
        {
            "device_intelligence": {
                "fingerprint": "blocked-device",
                "status": "BLOCKED",
                "is_new_device": False,
            },
        },
    )

    assert result["risk_score"] == 80
    assert result["risk_level"] == "HIGH"
    assert result["action"] == "BLOCK"


def test_correlated_takeover_signals_produce_lock_recommendation():
    result = analyze_event(
        {
            "user_id": "acct_correlated_ato",
            "amount": 0,
            "device": "android",
            "ip": "102.88.45.29",
            "location": "kenya",
            "event_type": "login_success",
            "timestamp": "2026-06-19T12:00:00",
        },
        {
            "account_takeover": {
                "signals": [
                    {
                        "category": "ACCOUNT_TAKEOVER",
                        "label": "New device after SIM change",
                        "points": 55,
                        "evidence": "New device appeared shortly after a SIM change",
                    },
                    {
                        "category": "ACCOUNT_TAKEOVER",
                        "label": "Successful login after failure burst",
                        "points": 45,
                        "evidence": "Successful login followed repeated failures",
                    },
                ],
            },
        },
    )

    assert result["account_takeover"]["detected"] is True
    assert result["account_takeover"]["score"] == 100
    assert result["account_takeover"]["recommendation"] == "LOCK_ACCOUNT"
    assert result["action"] == "LOCK_ACCOUNT"
