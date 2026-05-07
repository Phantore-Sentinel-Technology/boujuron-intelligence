from infrastructure.risk_engine.behavior import update_profile


def test_behavior_profile_creation():
    event = {
        "user_id": "user100",
        "device_type": "iphone",
        "ip": "192.168.1.1",
        "timestamp": "2026-05-04T12:00:00"
    }

    profile = update_profile(event)

    assert "known_device" in profile
