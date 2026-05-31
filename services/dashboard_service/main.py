import psycopg2
import asyncio
from fastapi import FastAPI, Query, WebSocket
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from config.settings import settings
from infrastructure.fraud_detection.scoring import calculate_risk_score, get_risk_level
from services.dashboard_service.schemas import EventResponse, FraudAlertResponse
from pathlib import Path
app = FastAPI(title="Boujuron Dashboard API")

clients = []
FRONTEND_DIST = Path("frontend/dist")

if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

def get_db():
    conn = psycopg2.connect(settings.DATABASE_URL)
    return conn, conn.cursor()

@app.get("/", response_class=HTMLResponse)
def serve_dashboard():
    react_index = FRONTEND_DIST / "index.html"
    if react_index.exists():
        return FileResponse(react_index)

    html_path = Path("dashboard.html")
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))

@app.websocket("/ws/fraud")
async def ws_fraud(websocket: WebSocket):
    await websocket.accept()
    clients.append(websocket)

    try:
        while True:
            await asyncio.sleep(1)
    except:
        clients.remove(websocket)

@app.post("/internal/fraud")
async def push_fraud(event: dict):
    for client in clients:
        await client.send_json(event)
    return {"status": "sent"}


@app.get("/events", response_model=list[EventResponse])
def get_events(limit: int = Query(50)):
    conn, cursor = get_db()

    cursor.execute("""
        SELECT user_id, event_type, device_type, ip, timestamp
        FROM events ORDER BY id DESC LIMIT %s
    """, (limit,))

    rows = cursor.fetchall()

    conn.close()

    return [EventResponse(*row) for row in rows]

@app.get("/fraud-alerts", response_model=list[FraudAlertResponse])
def get_fraud(limit: int = Query(50)):
    conn, cursor = get_db()

    for column_name, column_type in (
        ("recommended_action", "TEXT"),
        ("confidence", "NUMERIC"),
        ("signals_triggered", "INTEGER"),
        ("behavioral_match", "BOOLEAN"),
    ):
        cursor.execute(f"""
            ALTER TABLE fraud_alerts
            ADD COLUMN IF NOT EXISTS {column_name} {column_type}
        """)

    conn.commit()

    cursor.execute("""
        SELECT
            user_id,
            reason,
            timestamp,
            risk_score,
            risk_level,
            recommended_action,
            confidence,
            signals_triggered,
            behavioral_match
        FROM fraud_alerts ORDER BY id DESC LIMIT %s
    """, (limit,))

    rows = cursor.fetchall()

    conn.close()

    return [
        FraudAlertResponse(
            user_id=r[0],
            reason=r[1],
            timestamp=str(r[2]),
            risk_score=str(r[3]),
            risk_level=r[4],
            recommended_action=r[5],
            confidence=float(r[6]) if r[6] is not None else None,
            signals_triggered=r[7],
            behavioral_match=r[8]
        )
        for r in rows
    ]

@app.get("/users/{user_id}/activity")
def get_user_activity(user_id: str):
    conn, cursor = get_db()

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

    conn.close()

    return {
        "events": events,
        "fraud_alerts": frauds
    }


@app.get("/ml-features")
def get_features(limit: int = 50):
    conn, cursor = get_db()

    cursor.execute("""
        SELECT user_id, num_devices, num_ips, total_requests, timestamp
        FROM ml_features ORDER BY id DESC LIMIT %s
    """, (limit,))

    rows = cursor.fetchall()

    conn.close()

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


@app.get("/{full_path:path}", response_class=HTMLResponse)
def serve_react_routes(full_path: str):
    react_index = FRONTEND_DIST / "index.html"
    if react_index.exists():
        return FileResponse(react_index)

    html_path = Path("dashboard.html")
    return HTMLResponse(content=html_path.read_text(encoding="utf-8"))
