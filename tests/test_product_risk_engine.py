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
            "known_devices": ["old-device-1"],
            "known_locations": ["nigeria"],
        },
    )

    assert result["risk_score"] >= 70
    assert result["risk_level"] == "CRITICAL"
    assert result["action"] == "LOCK_ACCOUNT"
    assert result["recommendation"] == "LOCK_ACCOUNT_AND_ESCALATE"


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
    assert result["recommendation"] == "LOCK_ACCOUNT_AND_ESCALATE"
