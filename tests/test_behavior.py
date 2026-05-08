from infrastructure.risk_engine.behavior import update_profile


def test_behavior_profile_creation():
    event = {
        "user_id": "user100",
        "device_type": "iphone",
        "ip": "192.168.1.1",
        "timestamp": "2026-05-04T12:00:00"
    }

    profile = update_profile(event)

    assert "known_devices" in profile
    assert "known_ips" in profile
    assert "total_requests" in profile

    assert isinstance(profile["known_devices"], list)
    assert isinstance(profile["known_ips"], list)

    assert profile["total_requests"] == 1


def test_behavior_profile_updates():
    event = {
        "user_id": "user100",
        "device_type": "android",
        "ip": "10.0.0.2",
        "timestamp": "2026-05-04T13:00:00"
    }

    profile = update_profile(event)

    assert isinstance(profile["known_devices"], list)
    assert isinstance(profile["known_ips"], list)

    assert profile["total_requests"] >= 1