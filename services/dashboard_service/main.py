from fastapi import FastAPI, Query, WebSocket
import sqlite3

from services.dashboard_service.schemas import EventResponse, FraudAlertResponse
from infrastructure.fraud_detection.scoring import calculate_risk_score, get_risk_level

app = FastAPI(title="Phantore Sentinel Dashboard API")

conn = sqlite3.connect("events.db", check_same_thread=False)
cursor = conn.cursor()

clients = []


@app.websocket("/ws/fraud")
async def ws_fraud(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        clients.remove(websocket)

@app.post("internal/fraud")
async def push_fraud(event: dict):
    for client in clients:
        await client.send_json(event)
    return {"status": "sent"}


# 🔹 GET EVENTS
@app.get("/events", response_model=list[EventResponse])
def get_events(limit: int = Query(50)):
    cursor.execute(
        "SELECT user_id, event_type, device_type, ip, timestamp FROM events ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()

    return [
        EventResponse(
            user_id=row[0],
            event_type=row[1],
            device_type=row[2],
            ip=row[3],
            timestamp=row[4]
        )
        for row in rows
    ]


# 🔹 GET FRAUD ALERTS
@app.get("/fraud-alerts", response_model=list[FraudAlertResponse])
def get_fraud(limit: int = Query(50)):
    cursor.execute(
        "SELECT user_id, reason, timestamp FROM fraud_alerts ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = cursor.fetchall()

    results = []
    for row in rows:
        score = calculate_risk_score(row[1])

        results.append(
            FraudAlertResponse(
                user_id=row[0],
                reason=row[1],
                timestamp=row[2],
                risk_score=score,
                risk_level=get_risk_level(score)
            )
        )

    return results


# 🔹 FILTER BY USER
@app.get("/users/{user_id}/activity")
def get_user_activity(user_id: str):
    cursor.execute(
        "SELECT user_id, event_type, device_type, ip, timestamp FROM events WHERE user_id = ?",
        (user_id,)
    )
    events = cursor.fetchall()

    cursor.execute(
        "SELECT user_id, reason, timestamp FROM fraud_alerts WHERE user_id = ?",
        (user_id,)
    )
    frauds = cursor.fetchall()

    return {
        "events": events,
        "fraud_alerts": frauds
    }

@app.get("/ml-features")
def get_features(limit: int = 50):
    cursor.execute("""
    SELECT user_id, num_devices, num_ips, total_requests, timestamp
    FROM ml_features ORDER BY id DESC LIMIT ?
    """, (limit,))

    rows = cursor.fetchall()

    return [
        {
            "user_id": r[0],
            "num_devices": r[1],
            "num_ips": r[2],
            "total_requests": r[3],
            "timestamp": r[4]
        }
        for r in rows
    ]