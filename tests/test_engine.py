from infrastructure.risk_engine.engine import process_event


def test_normal_event():
    event = {
        "user_id": "user1",
        "event_type": "login",
        "device_type": "iphone",
        "ip": "192.168.1.1",
        "timestamp": "2026-05-04T14:00:00"
    }

    result = process_event(event)

    assert "risk_score" in result
    assert "risk_level" in result
    assert "reasons" in result

    assert result["risk_level"] in ["LOW", "MEDIUM", "HIGH"]


def test_suspicious_event():
    event = {
        "user_id": "user1",
        "event_type": "login",
        "device_type": "unknown_android",
        "ip": "203.45.11.90",
        "timestamp": "2026-05-04T02:00:00"
    }

    result = process_event(event)

    assert result["risk_score"] >= 0
    assert isinstance(result["reasons"], list)
