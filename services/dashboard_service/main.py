import psycopg2
from fastapi import FastAPI, Query, WebSocket

from config.settings import settings
from infrastructure.fraud_detection.scoring import calculate_risk_score, get_risk_level
from services.dashboard_service.schemas import EventResponse, FraudAlertResponse

app = FastAPI(title="Phantore Sentinel Dashboard API")

conn = psycopg2.connect(settings.DATABASE_URL)
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


@app.post("/internal/fraud")
async def push_fraud(event: dict):
    for client in clients:
        await client.send_json(event)
    return {"status": "sent"}


@app.get("/events", response_model=list[EventResponse])
def get_events(limit: int = Query(50)):
    cursor.execute("""
        SELECT user_id, event_type, device_type, ip, timestamp
        FROM events ORDER BY id DESC LIMIT %s
    """, (limit,))
    rows = cursor.fetchall()

    return [EventResponse(*row) for row in rows]


@app.get("/fraud-alerts", response_model=list[FraudAlertResponse])
def get_fraud(limit: int = Query(50)):
    cursor.execute("""
        SELECT user_id, reason, timestamp, risk_score, risk_level
        FROM fraud_alerts ORDER BY id DESC LIMIT %s
    """, (limit,))
    rows = cursor.fetchall()

    return [
        FraudAlertResponse(
            user_id=r[0],
            reason=r[1],
            timestamp=str(r[2]),
            risk_score=str(r[3]),
            risk_level=r[4]
        )
        for r in rows
    ]


@app.get("/users/{user_id}/activity")
def get_user_activity(user_id: str):
    cursor.execute("""
        SELECT user_id, event_type, device_type, ip, timestamp
        FROM events WHERE user_id = %s
    """, (user_id,))
    events = cursor.fetchall()

    cursor.execute("""
        SELECT user_id, reason, timestamp
        FROM fraud_alerts WHERE user_id = %s
    """, (user_id,))
    frauds = cursor.fetchall()

    return {"events": events, "fraud_alerts": frauds}


@app.get("/ml-features")
def get_features(limit: int = 50):
    cursor.execute("""
        SELECT user_id, num_devices, num_ips, total_requests, timestamp
        FROM ml_features ORDER BY id DESC LIMIT %s
    """, (limit,))
    rows = cursor.fetchall()

    return [
        {
            "user_id": r[0],
            "num_devices": r[1],
            "num_ips": r[2],
            "total_requests": r[3],
            "timestamp": str(r[4])
        }
        for r in rows
    ]
