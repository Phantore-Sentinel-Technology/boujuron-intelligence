from fastapi.testclient import TestClient
from services.risk_engine_service.main import app

client = TestClient(app)


def test_risk_score_endpoint():
    payload = {
        "user_id": "user999",
        "event_type": "login",
        "device_type": "iphone",
        "ip": "192.168.1.1",
        "timestamp": "2026-05-04T14:00:00"
    }

    response = client.post("/risk-score", json=payload)

    assert response.status_code == 200

    data = response.json()

    assert "risk_score" in data
    assert "risk_level" in data
    assert "reasons" in data


def test_invalid_payload():
    payload = {
        "user_id": "user999"
    }

    response = client.post("/risk-score", json=payload)

    assert response.status_code in [400, 422]

