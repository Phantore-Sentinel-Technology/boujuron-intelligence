from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime

from services.risk_engine_service.engine import analyze_event

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
    amount: float = Field(default=0, ge=0)
    device: str | None = None
    device_type: str | None = None
    device_id: str | None = None
    ip: str = Field(min_length=1, max_length=160)
    location: str = ""
    network: str = ""
    event_type: str = "transaction"
    timestamp: str | None = None
    is_rooted: bool = False
    is_emulator: bool = False
    browser_tampering: bool = False
    sim_swap_detected: bool = False
    password_changed_recently: bool = False
    failed_login_count: int = Field(default=0, ge=0)


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
    event_data = event.model_dump()
    event_data["timestamp"] = event.timestamp or datetime.utcnow().isoformat()
    result = analyze_event(event_data)

    alert = {
        "user_id": event.user_id,
        "reason": result["reason"],
        "risk_score": result["risk_score"],
        "risk_level": result["risk_level"],
        "timestamp": event_data["timestamp"],
        "recommended_action": result["recommendation"],
        "confidence": result["confidence"],
        "signals_triggered": len(result["signals"]),
        "behavioral_match": result["behavioral_match"],
    }

    fraud_alerts.insert(0, alert)

    disconnected = []

    for connection in connections:
        try:
            await connection.send_json(alert)
        except:
            disconnected.append(connection)

    for dc in disconnected:
        connections.remove(dc)

    return {
        "user_id": event.user_id,
        "risk_score": result["risk_score"],
        "risk_level": result["risk_level"],
        "action": result["action"],
        "recommendation": result["recommendation"],
        "confidence": result["confidence"],
        "reasons": result["reasons"],
        "signals": result["signals"],
        "behavioral_match": result["behavioral_match"],
        "timestamp": event_data["timestamp"],
    }

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
