from infrastructure.risk_engine.engine import check_rules


def test_multiple_ips_rules():
    profile = {
        "known_ips": [
            "192.168.1.1",
            "10.0.0.1"
        ],
        "known_devices": ["iphone"],
        "total_requests": 2
    }

    event = {
        "ip": "203.45.11.90",
        "device_type": "iphone"
    }

    score, reasons = check_rules(event, profile)
    assert score >= 0
    assert isinstance(reasons, list)


def test_new_device_rule():
    profile = {
        "known_ips": ["192.168.1.1"],
        "known_devices": ["iphone"],
        "total_requests": 1
    }

    event = {
        "ip": "192.168.1.1",
        "device_type": "android"
    }

    score, reasons = check_rules(event, profile)

    assert isinstance(reasons, list)
