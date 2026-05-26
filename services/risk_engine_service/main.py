from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List
from datetime import datetime

from services.risk_engine_service.engine import process_event

app = FastAPI()

# STORE ALERTS IN MEMORY
fraud_alerts = []

# ACTIVE WEBSOCKET CONNECTIONS
connections: List[WebSocket] = []


# =========================
# REQUEST MODEL
# =========================
class Event(BaseModel):
    user_id: str
    event_type: str
    device_type: str
    ip: str
    timestamp: str


# =========================
# ROOT
# =========================
@app.get("/")
def home():
    return {"message": "Boujuron Intelligence API Running"}


# =========================
# RISK SCORING
# =========================
@app.post("/risk-score")
async def risk_score(event: Event):

    result = process_event(event.model_dump())

    alert = {
        "user_id": event.user_id,
        "reason": result["reason"],
        "risk_score": result["risk_score"],
        "risk_level": result["risk_level"],
        "timestamp": event.timestamp
    }

    # SAVE ALERT
    fraud_alerts.insert(0, alert)

    # SEND TO WEBSOCKET CLIENTS
    disconnected = []

    for connection in connections:
        try:
            await connection.send_json(alert)
        except:
            disconnected.append(connection)

    for dc in disconnected:
        connections.remove(dc)

    return result


# =========================
# GET ALERTS
# =========================
@app.get("/fraud-alerts")
def get_alerts():
    return fraud_alerts


# =========================
# WEBSOCKET
# =========================
@app.websocket("/ws/fraud")
async def websocket_endpoint(websocket: WebSocket):

    await websocket.accept()

    connections.append(websocket)

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:

        if websocket in connections:
            connections.remove(websocket)