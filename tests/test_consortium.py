from services.dashboard_service.main import device_fingerprint, reputation_hash


def test_device_fingerprint_is_stable_for_same_device_id():
    first = device_fingerprint({"device_id": "Phone-ABC", "browser": "Chrome"})
    second = device_fingerprint({"device_id": "phone-abc", "browser": "Safari"})
    assert first == second


def test_consortium_hashes_are_type_scoped_and_do_not_expose_raw_values():
    ip_hash = reputation_hash("IP", "102.88.45.21")
    device_hash = reputation_hash("DEVICE", "102.88.45.21")
    assert ip_hash != device_hash
    assert "102.88.45.21" not in ip_hash
