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
    assert "Debit amount spike" in labels
    assert result["risk_level"] == "MEDIUM"
    assert result["action"] == "STEP_UP_VERIFY"
    assert result["recommendation"] == "STEP_UP_VERIFY"


def test_rooted_new_device_and_vpn_is_high_hold_for_review():
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
    assert result["risk_level"] == "HIGH"
    assert result["action"] == "HOLD_FOR_REVIEW"
    assert result["recommendation"] == "HOLD_FOR_REVIEW"


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
    assert result["action"] == "PND_OR_BLOCK"
    assert result["recommendation"] == "PND_OR_BLOCK"


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

    assert "Repetitive outflow pattern" in result["reasons"]
    assert result["risk_level"] == "MEDIUM"
    assert result["action"] == "STEP_UP_VERIFY"


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
    assert result["action"] == "HOLD_FOR_REVIEW"


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
    assert result["account_takeover"]["recommendation"] == "PND_OR_BLOCK"
    assert result["action"] == "PND_OR_BLOCK"


def test_explicit_repetitive_outflow_count_triggers_at_five():
    result = analyze_event(
        {
            "user_id": "acct_repetitive",
            "amount": 20_000,
            "transaction_direction": "DEBIT",
            "event_type": "wallet_transfer",
            "repetitive_outflow_count": 5,
            "device": "iphone",
            "ip": "102.88.45.30",
            "location": "nigeria",
            "timestamp": "2026-06-19T12:00:00",
        },
        {
            "trusted_event_count": 6,
            "settings": {
                "minimum_profile_events": 3,
                "velocity_window_minutes": 10,
                "velocity_points": 40,
            },
        },
    )

    assert "Repetitive outflow pattern" in result["reasons"]
    assert result["risk_level"] == "MEDIUM"
    assert result["action"] == "STEP_UP_VERIFY"

def test_watchlisted_inflow_ip_triggers_critical_account_protection():
    result = analyze_event({
        "user_id": "acct_watchlisted_credit",
        "transaction_direction": "CREDIT",
        "amount": 150_000,
        "event_type": "credit",
        "device": "iphone",
        "ip": "102.88.45.90",
        "counterparty_ip": "45.90.12.10",
        "location": "nigeria",
        "timestamp": "2026-06-19T12:00:00",
    })

    assert "Incoming credit from watchlisted IP" in result["reasons"]
    assert result["risk_level"] == "CRITICAL"
    assert result["action"] == "PND_OR_BLOCK"


def test_three_failed_login_attempts_lock_device():
    result = analyze_event({
        "user_id": "acct_failed_login",
        "amount": 0,
        "event_type": "login_failure",
        "failed_login_count": 3,
        "device": "android",
        "ip": "102.88.45.91",
        "location": "nigeria",
        "timestamp": "2026-06-19T12:00:00",
    })

    assert "Device locked after 3 failed login attempts" in result["reasons"]
    assert result["risk_level"] == "CRITICAL"
    assert result["action"] == "PND_OR_BLOCK"


def test_same_bank_account_per_device_policy_triggers():
    result = analyze_event(
        {
            "user_id": "acct_device_policy",
            "transaction_direction": "DEBIT",
            "amount": 20_000,
            "event_type": "wallet_transfer",
            "device": "iphone",
            "ip": "102.88.45.92",
            "location": "nigeria",
            "timestamp": "2026-06-19T12:00:00",
        },
        {
            "historical_account": {
                "same_bank_device_account_count": 1,
            },
        },
    )

    assert "Device already tied to another account in this bank" in result["reasons"]
    assert result["risk_level"] in {"HIGH", "CRITICAL"}


def test_historical_account_trend_break_adds_signal():
    result = analyze_event(
        {
            "user_id": "acct_history",
            "transaction_direction": "DEBIT",
            "amount": 800_000,
            "event_type": "wallet_transfer",
            "device": "iphone",
            "ip": "102.88.45.93",
            "location": "nigeria",
            "timestamp": "2026-06-19T12:00:00",
        },
        {
            "historical_account": {
                "historical_event_count": 12,
                "historical_debit_average": 50_000,
            },
        },
    )

    assert "Transaction breaks historical account trend" in result["reasons"]
