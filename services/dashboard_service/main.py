import asyncio
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from collections import Counter
from datetime import datetime
from statistics import mean

import psycopg2
from fastapi import Depends, FastAPI, Header, HTTPException, Query, WebSocket
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from config.settings import settings
from services.dashboard_service.schemas import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthTokenResponse,
    AuthUserResponse,
    EventResponse,
    FraudAlertResponse,
    ScoreBreakdownItem,
    UserProfileEvent,
    UserProfileResponse,
)
from pathlib import Path
app = FastAPI(title="Boujuron Dashboard API")

clients = []
FRONTEND_DIST = Path("frontend/dist")
AUTH_SECRET = os.getenv("JWT_SECRET", "boujuron-local-development-secret")
TOKEN_TTL_SECONDS = 60 * 60 * 12
ALLOWED_ROLES = {"Admin", "Fraud Analyst", "Investigator", "Read-Only Auditor"}

if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

def get_db():
    conn = psycopg2.connect(settings.DATABASE_URL)
    return conn, conn.cursor()


def ensure_auth_tables(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS app_users (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000).hex()
    return f"{salt}:{digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, digest = stored.split(":", 1)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000).hex()
    return hmac.compare_digest(candidate, digest)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


def create_token(user: AuthUserResponse) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": user.email, "uid": user.id, "role": user.role, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    signing_input = f"{_b64(json.dumps(header).encode())}.{_b64(json.dumps(payload).encode())}"
    signature = hmac.new(AUTH_SECRET.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64(signature)}"


def decode_token(token: str) -> dict:
    try:
        signing_input, signature = token.rsplit(".", 1)
        expected = hmac.new(AUTH_SECRET.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64(expected), signature):
            raise ValueError("bad signature")
        payload = json.loads(_unb64(signing_input.split(".")[1]))
        if payload["exp"] < int(time.time()):
            raise ValueError("expired")
        return payload
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc


def get_current_user(authorization: str | None = Header(default=None)) -> AuthUserResponse:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    payload = decode_token(authorization.removeprefix("Bearer ").strip())
    conn, cursor = get_db()
    ensure_auth_tables(cursor)
    cursor.execute("SELECT id, name, email, role FROM app_users WHERE id = %s", (payload["uid"],))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return AuthUserResponse(id=row[0], name=row[1], email=row[2], role=row[3])


def parse_reasons(reason: str | None) -> list[str]:
    return [item.strip() for item in (reason or "").split(",") if item.strip()]


def build_score_breakdown(reason: str | None, total_score: int) -> list[ScoreBreakdownItem]:
    reasons = parse_reasons(reason)
    weights = {
        "rooted": 25,
        "tor": 20,
        "vpn": 15,
        "location": 15,
        "behavior": 10,
        "velocity": 12,
        "device": 15,
        "ip": 10,
        "network": 12,
    }
    breakdown = []
    remaining = max(total_score, 0)
    for raw_reason in reasons:
        lower = raw_reason.lower()
        points = next((value for keyword, value in weights.items() if keyword in lower), 8)
        points = min(points, remaining) if remaining else points
        breakdown.append(ScoreBreakdownItem(label=raw_reason.title(), points=points, evidence=raw_reason))
        remaining -= points
    if not breakdown and total_score:
        breakdown.append(ScoreBreakdownItem(label="Risk Engine Score", points=total_score, evidence="Aggregate fraud model output"))
    elif remaining > 0:
        breakdown.append(ScoreBreakdownItem(label="Model Baseline", points=remaining, evidence="Residual risk from combined signals"))
    return breakdown


def trend_from_scores(scores: list[int]) -> str:
    if len(scores) < 2:
        return "stable"
    latest, previous = scores[0], scores[1]
    if latest > previous:
        return "up"
    if latest < previous:
        return "down"
    return "stable"


def common_window(timestamps: list[str]) -> str:
    hours = []
    for value in timestamps:
        try:
            hours.append(datetime.fromisoformat(str(value).replace("Z", "+00:00")).hour)
        except ValueError:
            continue
    if not hours:
        return "Unknown"
    avg_hour = round(mean(hours))
    return f"{max(avg_hour - 2, 0):02d}:00 - {min(avg_hour + 2, 23):02d}:00"


@app.post("/auth/register", response_model=AuthTokenResponse)
def register(payload: AuthRegisterRequest):
    role = payload.role if payload.role in ALLOWED_ROLES else "Fraud Analyst"
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    conn, cursor = get_db()
    ensure_auth_tables(cursor)
    cursor.execute("SELECT id FROM app_users WHERE email = %s", (payload.email.lower(),))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=409, detail="Email is already registered")

    cursor.execute("""
        INSERT INTO app_users (name, email, password_hash, role)
        VALUES (%s, %s, %s, %s)
        RETURNING id, name, email, role
    """, (payload.name.strip(), payload.email.lower(), hash_password(payload.password), role))
    row = cursor.fetchone()
    conn.commit()
    conn.close()
    user = AuthUserResponse(id=row[0], name=row[1], email=row[2], role=row[3])
    return AuthTokenResponse(access_token=create_token(user), user=user)


@app.post("/auth/login", response_model=AuthTokenResponse)
def login(payload: AuthLoginRequest):
    conn, cursor = get_db()
    ensure_auth_tables(cursor)
    cursor.execute("SELECT id, name, email, role, password_hash FROM app_users WHERE email = %s", (payload.email.lower(),))
    row = cursor.fetchone()
    conn.close()
    if not row or not verify_password(payload.password, row[4]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user = AuthUserResponse(id=row[0], name=row[1], email=row[2], role=row[3])
    return AuthTokenResponse(access_token=create_token(user), user=user)


@app.get("/auth/me", response_model=AuthUserResponse)
def me(current_user: AuthUserResponse = Depends(get_current_user)):
    return current_user

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


@app.get("/customers/{user_id}/profile", response_model=UserProfileResponse)
def get_user_profile(user_id: str, current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()

    cursor.execute("""
        SELECT event_type, device_type, ip, location, network, amount, timestamp
        FROM events
        WHERE user_id = %s
        ORDER BY timestamp DESC NULLS LAST, id DESC
        LIMIT 25
    """, (user_id,))
    event_rows = cursor.fetchall()

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
        FROM fraud_alerts
        WHERE user_id = %s
        ORDER BY timestamp DESC NULLS LAST, id DESC
        LIMIT 20
    """, (user_id,))
    alert_rows = cursor.fetchall()
    conn.close()

    alerts = [
        FraudAlertResponse(
            user_id=r[0],
            reason=r[1],
            timestamp=str(r[2]),
            risk_score=str(r[3]),
            risk_level=r[4],
            recommended_action=r[5],
            confidence=float(r[6]) if r[6] is not None else None,
            signals_triggered=r[7],
            behavioral_match=r[8],
        )
        for r in alert_rows
    ]
    events = [
        UserProfileEvent(
            event_type=r[0],
            device_type=r[1],
            ip=r[2],
            location=r[3],
            network=r[4],
            amount=float(r[5]) if r[5] is not None else None,
            timestamp=str(r[6]),
        )
        for r in event_rows
    ]

    score_values = [int(float(alert.risk_score or 0)) for alert in alerts]
    current_score = score_values[0] if score_values else 0
    current_alert = alerts[0] if alerts else None
    device_counts = Counter(event.device_type for event in events if event.device_type)
    location_counts = Counter(event.location for event in events if event.location)
    known_devices = [device for device, count in device_counts.most_common() if count > 1][:5]
    new_devices = [device for device, count in device_counts.items() if count == 1][:5]
    known_locations = [location for location, count in location_counts.most_common() if count > 1][:5]
    amounts = [event.amount for event in events if event.amount is not None]

    return UserProfileResponse(
        user_id=user_id,
        current_risk=current_score,
        risk_level=current_alert.risk_level if current_alert else "LOW",
        risk_trend=trend_from_scores(score_values),
        known_devices=known_devices,
        new_devices=new_devices,
        known_locations=known_locations,
        current_location=events[0].location if events else None,
        ip_history=list(dict.fromkeys(event.ip for event in events if event.ip))[:8],
        behavioral_profile={
            "Normal Login Time": common_window([event.timestamp for event in events]),
            "Normal Device": device_counts.most_common(1)[0][0] if device_counts else "Unknown",
            "Normal Location": location_counts.most_common(1)[0][0] if location_counts else "Unknown",
            "Average Transaction": f"{round(mean(amounts), 2):,}" if amounts else "Unknown",
        },
        recent_events=events[:10],
        previous_investigations=alerts,
        score_breakdown=build_score_breakdown(current_alert.reason if current_alert else None, current_score),
    )


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
