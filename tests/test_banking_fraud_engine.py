from services.risk_engine_service.engine import analyze_event


def test_low_debit_allows_normal_activity():
    result = analyze_event({
        "user_id": "customer_101",
        "transaction_direction": "DEBIT",
        "amount": 2_500,
        "event_type": "airtime_purchase",
        "device_type": "iphone",
        "ip": "102.88.45.101",
        "location": "lagos, nigeria",
        "network": "MOBILE",
    })

    assert result["risk_level"] == "LOW"
    assert result["recommendation"] == "ALLOW"
    assert result["confidence"] >= 80


def test_medium_debit_requires_step_up_verification():
    result = analyze_event({
        "transaction_direction": "DEBIT",
        "amount": 1_000_000,
        "event_type": "wallet_transfer",
        "device_type": "iphone",
        "ip": "102.88.45.101",
        "location": "lagos, nigeria",
    })

    assert result["risk_level"] == "MEDIUM"
    assert result["recommendation"] == "STEP_UP_VERIFY"


def test_high_debit_is_held_for_review_not_hard_blocked():
    result = analyze_event({
        "transaction_direction": "DEBIT",
        "amount": 1_000_000,
        "event_type": "wallet_transfer",
        "device_type": "iphone",
        "ip": "102.88.45.101",
        "location": "lagos, nigeria",
        "new_beneficiary_added": True,
    })

    assert result["risk_level"] == "HIGH"
    assert result["recommendation"] == "HOLD_FOR_REVIEW"


def test_critical_debit_uses_pnd_only_with_strong_confidence():
    result = analyze_event({
        "transaction_direction": "DEBIT",
        "amount": 2_500_000,
        "event_type": "large_transfer",
        "device_type": "rooted device",
        "ip": "45.90.12.10",
        "location": "russia",
        "network": "TOR",
    })

    assert result["risk_level"] == "CRITICAL"
    assert result["confidence"] >= 85
    assert result["recommendation"] == "PND_OR_BLOCK"


def test_credit_rules_detect_suspicious_inflow_patterns():
    result = analyze_event({
        "transaction_direction": "CREDIT",
        "amount": 3_000_000,
        "event_type": "credit",
        "device_type": "android",
        "ip": "102.88.45.101",
        "location": "lagos, nigeria",
        "rapid_credit_count": 4,
        "different_sender_count": 3,
        "debits_after_credit_count": 1,
    })

    assert result["transaction_direction"] == "CREDIT"
    assert result["risk_level"] == "CRITICAL"
    assert "Multiple rapid credits from different sources" in result["reasons"]
    assert "Credits followed quickly by suspicious debits" in result["reasons"]
