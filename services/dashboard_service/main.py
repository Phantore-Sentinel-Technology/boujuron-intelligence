import asyncio
import base64
import csv
import hashlib
import hmac
import io
import json
import os
import secrets
import time
from collections import Counter
from datetime import datetime
from statistics import mean

import psycopg2
from fastapi import Depends, FastAPI, Header, HTTPException, Query, WebSocket
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from config.settings import settings
from services.dashboard_service.schemas import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthTokenResponse,
    AuthUserResponse,
    AnalystPerformanceResponse,
    AnalyticsOverviewResponse,
    CaseDetailResponse,
    CaseNoteRequest,
    CaseNoteResponse,
    CaseSummaryResponse,
    CaseTimelineResponse,
    CaseUpdateRequest,
    EventResponse,
    FraudAlertResponse,
    BehaviorAnomaly,
    FraudHeatMapPointResponse,
    IntelligenceActivityResponse,
    InvestigationFeedItemResponse,
    NotificationResponse,
    RiskTimelinePoint,
    RiskDistributionResponse,
    ScoreBreakdownItem,
    TrendPointResponse,
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
CASE_STATUSES = {"NEW", "ASSIGNED", "INVESTIGATING", "ESCALATED", "RESOLVED", "ARCHIVED"}
CASE_PRIORITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
ANALYST_FEEDBACK = {"TRUE_FRAUD", "FALSE_POSITIVE", "NEEDS_REVIEW"}
CASE_DECISIONS = {"ALLOW", "VERIFY", "BLOCK", "FREEZE", "ESCALATE"}

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


def ensure_event_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id SERIAL PRIMARY KEY,
            transaction_id TEXT,
            user_id TEXT,
            amount NUMERIC,
            location TEXT,
            event_type TEXT,
            device_type TEXT,
            network TEXT,
            ip TEXT,
            timestamp TIMESTAMP
        )
    """)
    for column_name, column_type in (
        ("transaction_id", "TEXT"),
        ("amount", "NUMERIC"),
        ("location", "TEXT"),
        ("network", "TEXT"),
    ):
        cursor.execute(f"""
            ALTER TABLE events
            ADD COLUMN IF NOT EXISTS {column_name} {column_type}
        """)


def ensure_fraud_alert_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fraud_alerts (
            id SERIAL PRIMARY KEY,
            user_id TEXT,
            reason TEXT,
            risk_score INTEGER,
            risk_level TEXT,
            timestamp TIMESTAMP
        )
    """)
    ensure_fraud_alert_columns(cursor)


def ensure_case_tables(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cases (
            id SERIAL PRIMARY KEY,
            case_number TEXT UNIQUE,
            fraud_alert_id INTEGER UNIQUE,
            user_id TEXT NOT NULL,
            reason TEXT DEFAULT '',
            risk_score INTEGER DEFAULT 0,
            risk_level TEXT DEFAULT 'LOW',
            status TEXT DEFAULT 'NEW',
            priority TEXT DEFAULT 'LOW',
            assigned_to TEXT,
            assigned_at TIMESTAMP,
            analyst_feedback TEXT,
            decision TEXT,
            recommended_action TEXT,
            potential_loss NUMERIC,
            actual_loss NUMERIC,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            resolved_at TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS case_notes (
            id SERIAL PRIMARY KEY,
            case_id INTEGER REFERENCES cases(id) ON DELETE CASCADE,
            author TEXT NOT NULL,
            note TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS case_timeline (
            id SERIAL PRIMARY KEY,
            case_id INTEGER REFERENCES cases(id) ON DELETE CASCADE,
            event_type TEXT NOT NULL,
            description TEXT NOT NULL,
            actor TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def ensure_fraud_alert_columns(cursor):
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


def prepare_analytics_tables(cursor):
    ensure_event_table(cursor)
    ensure_fraud_alert_table(cursor)
    ensure_case_tables(cursor)
    materialize_cases_from_alerts(cursor)


def csv_response(filename: str, headers: list[str], rows: list[tuple]) -> Response:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(headers)
    writer.writerows(rows)
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def simple_pdf(title: str, lines: list[str]) -> bytes:
    escaped_lines = [line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") for line in lines]
    text = [f"BT /F1 18 Tf 72 760 Td ({title}) Tj ET"]
    y = 724
    for line in escaped_lines:
        text.append(f"BT /F1 11 Tf 72 {y} Td ({line}) Tj ET")
        y -= 18
        if y < 72:
            break
    stream = "\n".join(text).encode("utf-8")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = io.BytesIO()
    pdf.write(b"%PDF-1.4\n")
    offsets = []
    for index, obj in enumerate(objects, start=1):
        offsets.append(pdf.tell())
        pdf.write(f"{index} 0 obj\n".encode("ascii"))
        pdf.write(obj)
        pdf.write(b"\nendobj\n")
    xref = pdf.tell()
    pdf.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode("ascii"))
    for offset in offsets:
        pdf.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.write(f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode("ascii"))
    return pdf.getvalue()


def priority_from_risk(risk_level: str | None) -> str:
    level = (risk_level or "LOW").upper()
    return level if level in CASE_PRIORITIES else "LOW"


def materialize_cases_from_alerts(cursor):
    ensure_fraud_alert_table(cursor)
    cursor.execute("""
        SELECT
            id,
            user_id,
            reason,
            risk_score,
            risk_level,
            recommended_action,
            timestamp
        FROM fraud_alerts
        ORDER BY id ASC
    """)
    alerts = cursor.fetchall()
    for alert in alerts:
        alert_id, user_id, reason, risk_score, risk_level, recommended_action, timestamp = alert
        cursor.execute("SELECT id FROM cases WHERE fraud_alert_id = %s", (alert_id,))
        if cursor.fetchone():
            continue

        cursor.execute("""
            INSERT INTO cases (
                case_number,
                fraud_alert_id,
                user_id,
                reason,
                risk_score,
                risk_level,
                priority,
                recommended_action,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, CURRENT_TIMESTAMP), CURRENT_TIMESTAMP)
            RETURNING id
        """, (
            f"CASE-{alert_id:04d}",
            alert_id,
            user_id,
            reason or "",
            int(risk_score or 0),
            risk_level or "LOW",
            priority_from_risk(risk_level),
            recommended_action,
            timestamp,
        ))
        case_id = cursor.fetchone()[0]
        cursor.execute("""
            INSERT INTO case_timeline (case_id, event_type, description, actor)
            VALUES (%s, %s, %s, %s)
        """, (case_id, "CASE_CREATED", "Case opened from fraud alert", "System"))


def timeline(cursor, case_id: int, event_type: str, description: str, actor: str):
    cursor.execute("""
        INSERT INTO case_timeline (case_id, event_type, description, actor)
        VALUES (%s, %s, %s, %s)
    """, (case_id, event_type, description, actor))


def row_to_case_summary(row) -> CaseSummaryResponse:
    return CaseSummaryResponse(
        id=row[0],
        case_number=row[1],
        user_id=row[2],
        risk_score=row[3],
        risk_level=row[4],
        status=row[5],
        priority=row[6],
        assigned_to=row[7],
        analyst_feedback=row[8],
        created_at=str(row[9]),
        updated_at=str(row[10]),
    )


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


def build_behavior_anomalies(events: list[UserProfileEvent], alerts: list[FraudAlertResponse]) -> list[BehaviorAnomaly]:
    anomalies: list[BehaviorAnomaly] = []
    if events:
        latest = events[0]
        historical_devices = {event.device_type for event in events[1:] if event.device_type}
        historical_locations = {event.location for event in events[1:] if event.location}
        amounts = [event.amount for event in events[1:] if event.amount is not None]
        latest_network = (latest.network or "").upper()
        latest_device = (latest.device_type or "").lower()

        if latest.device_type and historical_devices and latest.device_type not in historical_devices:
            anomalies.append(BehaviorAnomaly(label="New Device", severity="HIGH", detail=f"{latest.device_type} is not part of the historical device pattern"))
        if latest.location and historical_locations and latest.location not in historical_locations:
            anomalies.append(BehaviorAnomaly(label="Unusual Location", severity="HIGH", detail=f"Current activity from {latest.location} differs from known locations"))
        if "TOR" in latest_network or "VPN" in latest_network:
            anomalies.append(BehaviorAnomaly(label="Anonymous Network", severity="CRITICAL", detail=f"{latest.network} network observed on latest event"))
        if "root" in latest_device:
            anomalies.append(BehaviorAnomaly(label="Rooted Device", severity="CRITICAL", detail=f"{latest.device_type} indicates elevated device risk"))
        if latest.amount is not None and amounts:
            avg_amount = mean(amounts)
            if avg_amount and latest.amount >= avg_amount * 5:
                anomalies.append(BehaviorAnomaly(label="Transfer Spike", severity="HIGH", detail=f"Latest amount is {round(latest.amount / avg_amount, 1)}x above normal"))

    for reason in parse_reasons(alerts[0].reason if alerts else None):
        lower = reason.lower()
        if any(keyword in lower for keyword in ("behavior", "velocity", "tor", "rooted", "location")):
            label = reason.title()
            if not any(item.label == label for item in anomalies):
                anomalies.append(BehaviorAnomaly(label=label, severity="MEDIUM", detail=reason))

    return anomalies[:8]


def notification_from_row(row) -> NotificationResponse:
    event_id, event_type, description, actor, created_at, case_id, case_number, user_id, risk_level, status, assigned_to = row
    severity = "INFO"
    title = "Investigation update"
    if risk_level == "CRITICAL" or status == "ESCALATED":
        severity = "CRITICAL"
        title = "Critical investigation update"
    elif event_type in {"ASSIGNED_TO", "STATUS"} or status in {"NEW", "ASSIGNED"}:
        severity = "HIGH"
        title = "Case workflow update"
    elif event_type == "NOTE_ADDED":
        title = "Analyst comment added"

    if assigned_to:
        message = f"{case_number} for {user_id}: {description}. Assigned to {assigned_to}."
    else:
        message = f"{case_number} for {user_id}: {description}."

    return NotificationResponse(
        id=f"timeline-{event_id}",
        title=title,
        message=message,
        severity=severity,
        case_id=case_id,
        user_id=user_id,
        created_at=str(created_at),
    )


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

    ensure_fraud_alert_columns(cursor)
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
            "Average Events/Day": str(round(len(events) / max(len({event.timestamp[:10] for event in events if event.timestamp}), 1), 1)) if events else "Unknown",
        },
        behavior_anomalies=build_behavior_anomalies(events, alerts),
        risk_timeline=[
            RiskTimelinePoint(
                timestamp=alert.timestamp,
                score=int(float(alert.risk_score or 0)),
                level=alert.risk_level,
                reason=alert.reason,
            )
            for alert in reversed(alerts)
        ],
        recent_events=events[:10],
        previous_investigations=alerts,
        score_breakdown=build_score_breakdown(current_alert.reason if current_alert else None, current_score),
    )


@app.get("/intelligence/activity", response_model=IntelligenceActivityResponse)
def get_intelligence_activity(limit: int = Query(30), current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    ensure_case_tables(cursor)
    materialize_cases_from_alerts(cursor)
    conn.commit()

    cursor.execute("""
        SELECT
            t.id,
            t.event_type,
            t.description,
            t.actor,
            t.created_at,
            c.id,
            c.case_number,
            c.user_id,
            c.risk_level,
            c.status,
            c.assigned_to
        FROM case_timeline t
        JOIN cases c ON c.id = t.case_id
        ORDER BY t.created_at DESC, t.id DESC
        LIMIT %s
    """, (limit,))
    rows = cursor.fetchall()
    conn.close()

    notifications = [notification_from_row(row) for row in rows[:12]]
    feed = [
        InvestigationFeedItemResponse(
            id=f"timeline-{row[0]}",
            event_type=row[1],
            description=row[2],
            actor=row[3],
            created_at=str(row[4]),
            case_id=row[5],
            case_number=row[6],
            user_id=row[7],
            risk_level=row[8],
        )
        for row in rows
    ]
    return IntelligenceActivityResponse(notifications=notifications, feed=feed)


@app.get("/cases", response_model=list[CaseSummaryResponse])
def get_cases(
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    analyst: str | None = Query(default=None),
    risk_level: str | None = Query(default=None),
    current_user: AuthUserResponse = Depends(get_current_user),
):
    conn, cursor = get_db()
    ensure_case_tables(cursor)
    materialize_cases_from_alerts(cursor)
    conn.commit()

    cursor.execute("""
        SELECT
            id,
            case_number,
            user_id,
            risk_score,
            risk_level,
            status,
            priority,
            assigned_to,
            analyst_feedback,
            created_at,
            updated_at
        FROM cases
        WHERE (%s IS NULL OR status = %s)
          AND (%s IS NULL OR priority = %s)
          AND (%s IS NULL OR assigned_to = %s)
          AND (%s IS NULL OR risk_level = %s)
        ORDER BY
            CASE priority
                WHEN 'CRITICAL' THEN 4
                WHEN 'HIGH' THEN 3
                WHEN 'MEDIUM' THEN 2
                ELSE 1
            END DESC,
            updated_at DESC,
            id DESC
    """, (status, status, priority, priority, analyst, analyst, risk_level, risk_level))
    rows = cursor.fetchall()
    conn.close()
    return [row_to_case_summary(row) for row in rows]


@app.get("/cases/{case_id}", response_model=CaseDetailResponse)
def get_case(case_id: int, current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    ensure_case_tables(cursor)
    materialize_cases_from_alerts(cursor)
    conn.commit()

    cursor.execute("""
        SELECT
            id,
            case_number,
            user_id,
            risk_score,
            risk_level,
            status,
            priority,
            assigned_to,
            analyst_feedback,
            created_at,
            updated_at,
            reason,
            recommended_action,
            decision,
            potential_loss,
            actual_loss
        FROM cases
        WHERE id = %s
    """, (case_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Case not found")

    cursor.execute("""
        SELECT id, author, note, created_at
        FROM case_notes
        WHERE case_id = %s
        ORDER BY created_at DESC, id DESC
    """, (case_id,))
    note_rows = cursor.fetchall()

    cursor.execute("""
        SELECT id, event_type, description, actor, created_at
        FROM case_timeline
        WHERE case_id = %s
        ORDER BY created_at DESC, id DESC
    """, (case_id,))
    timeline_rows = cursor.fetchall()
    conn.close()

    summary = row_to_case_summary(row[:11])
    reason = row[11] or ""
    return CaseDetailResponse(
        **summary.model_dump(),
        reason=reason,
        recommended_action=row[12],
        decision=row[13],
        potential_loss=float(row[14]) if row[14] is not None else None,
        actual_loss=float(row[15]) if row[15] is not None else None,
        fraud_signals=parse_reasons(reason),
        score_breakdown=build_score_breakdown(reason, row[3]),
        notes=[
            CaseNoteResponse(id=r[0], author=r[1], note=r[2], created_at=str(r[3]))
            for r in note_rows
        ],
        timeline=[
            CaseTimelineResponse(id=r[0], event_type=r[1], description=r[2], actor=r[3], created_at=str(r[4]))
            for r in timeline_rows
        ],
    )


@app.patch("/cases/{case_id}", response_model=CaseDetailResponse)
def update_case(case_id: int, payload: CaseUpdateRequest, current_user: AuthUserResponse = Depends(get_current_user)):
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return get_case(case_id, current_user)

    validators = {
        "status": CASE_STATUSES,
        "priority": CASE_PRIORITIES,
        "analyst_feedback": ANALYST_FEEDBACK,
        "decision": CASE_DECISIONS,
    }
    for field, allowed in validators.items():
        if field in changes and changes[field] is not None and changes[field] not in allowed:
            raise HTTPException(status_code=400, detail=f"Invalid {field}")

    conn, cursor = get_db()
    ensure_case_tables(cursor)
    cursor.execute("""
        SELECT assigned_to, status, priority, analyst_feedback, decision, potential_loss, actual_loss
        FROM cases
        WHERE id = %s
    """, (case_id,))
    before = cursor.fetchone()
    if not before:
        conn.close()
        raise HTTPException(status_code=404, detail="Case not found")

    current_values = {
        "assigned_to": before[0],
        "status": before[1],
        "priority": before[2],
        "analyst_feedback": before[3],
        "decision": before[4],
        "potential_loss": float(before[5]) if before[5] is not None else None,
        "actual_loss": float(before[6]) if before[6] is not None else None,
    }

    set_clauses = ["updated_at = CURRENT_TIMESTAMP"]
    params = []
    for field, value in changes.items():
        set_clauses.append(f"{field} = %s")
        params.append(value)
    if "assigned_to" in changes and changes["assigned_to"]:
        set_clauses.append("assigned_at = CURRENT_TIMESTAMP")
    if changes.get("status") == "RESOLVED":
        set_clauses.append("resolved_at = CURRENT_TIMESTAMP")
    params.append(case_id)
    cursor.execute(f"UPDATE cases SET {', '.join(set_clauses)} WHERE id = %s", params)

    actor = current_user.name
    labels = {
        "assigned_to": "Assigned analyst",
        "status": "Status",
        "priority": "Priority",
        "analyst_feedback": "Analyst feedback",
        "decision": "Decision",
        "potential_loss": "Potential loss",
        "actual_loss": "Actual loss",
    }
    for field, value in changes.items():
        if current_values.get(field) != value:
            timeline(cursor, case_id, field.upper(), f"{labels[field]} changed to {value or 'Unassigned'}", actor)

    conn.commit()
    conn.close()
    return get_case(case_id, current_user)


@app.post("/cases/{case_id}/notes", response_model=CaseDetailResponse)
def add_case_note(case_id: int, payload: CaseNoteRequest, current_user: AuthUserResponse = Depends(get_current_user)):
    note = payload.note.strip()
    if not note:
        raise HTTPException(status_code=400, detail="Note cannot be empty")

    conn, cursor = get_db()
    ensure_case_tables(cursor)
    cursor.execute("SELECT id FROM cases WHERE id = %s", (case_id,))
    if not cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=404, detail="Case not found")

    cursor.execute("""
        INSERT INTO case_notes (case_id, author, note)
        VALUES (%s, %s, %s)
    """, (case_id, current_user.name, note))
    timeline(cursor, case_id, "NOTE_ADDED", "Investigation note added", current_user.name)
    cursor.execute("UPDATE cases SET updated_at = CURRENT_TIMESTAMP WHERE id = %s", (case_id,))
    conn.commit()
    conn.close()
    return get_case(case_id, current_user)


@app.get("/analytics/overview", response_model=AnalyticsOverviewResponse)
def analytics_overview(current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    prepare_analytics_tables(cursor)
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM events")
    total_events = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM fraud_alerts")
    fraud_alerts = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM cases WHERE analyst_feedback = 'TRUE_FRAUD'")
    confirmed = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM cases WHERE analyst_feedback = 'FALSE_POSITIVE'")
    false_positive = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM cases WHERE status = 'RESOLVED'")
    resolved = cursor.fetchone()[0]
    cursor.execute("""
        SELECT AVG(EXTRACT(EPOCH FROM (COALESCE(resolved_at, updated_at) - created_at)) / 60)
        FROM cases
        WHERE status IN ('RESOLVED', 'ARCHIVED')
    """)
    avg_minutes = cursor.fetchone()[0] or 0
    cursor.execute("SELECT COUNT(*) FROM cases WHERE decision IN ('BLOCK', 'FREEZE', 'ESCALATE') OR COALESCE(actual_loss, 0) = 0")
    prevented = cursor.fetchone()[0]
    conn.close()

    prevention_rate = round((prevented / fraud_alerts) * 100, 1) if fraud_alerts else 0
    false_positive_rate = round((false_positive / max(confirmed + false_positive, 1)) * 100, 1)
    return AnalyticsOverviewResponse(
        total_events=total_events,
        fraud_alerts=fraud_alerts,
        confirmed_fraud_cases=confirmed,
        fraud_prevention_rate=prevention_rate,
        false_positive_rate=false_positive_rate,
        average_investigation_minutes=round(float(avg_minutes), 1),
        cases_resolved=resolved,
    )


@app.get("/analytics/trends", response_model=list[TrendPointResponse])
def analytics_trends(current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    prepare_analytics_tables(cursor)
    conn.commit()
    cursor.execute("""
        SELECT COALESCE(DATE(timestamp)::TEXT, 'Unknown') AS day, COUNT(*)
        FROM fraud_alerts
        GROUP BY day
        ORDER BY day
        LIMIT 30
    """)
    rows = cursor.fetchall()
    conn.close()
    return [TrendPointResponse(label=r[0], value=r[1]) for r in rows]


@app.get("/analytics/risk-distribution", response_model=list[RiskDistributionResponse])
def analytics_risk_distribution(current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    prepare_analytics_tables(cursor)
    conn.commit()
    cursor.execute("""
        SELECT risk_level, COUNT(*)
        FROM fraud_alerts
        GROUP BY risk_level
    """)
    rows = cursor.fetchall()
    conn.close()
    counts = {r[0] or "LOW": r[1] for r in rows}
    return [RiskDistributionResponse(level=level, count=counts.get(level, 0)) for level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")]


@app.get("/analytics/analyst-performance", response_model=list[AnalystPerformanceResponse])
def analytics_analyst_performance(current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    prepare_analytics_tables(cursor)
    conn.commit()
    cursor.execute("""
        SELECT
            COALESCE(assigned_to, 'Unassigned') AS analyst,
            COUNT(*) AS assigned_cases,
            COUNT(*) FILTER (WHERE status IN ('RESOLVED', 'ARCHIVED')) AS resolved_cases,
            COUNT(*) FILTER (WHERE analyst_feedback = 'TRUE_FRAUD') AS confirmed_fraud,
            COUNT(*) FILTER (WHERE analyst_feedback = 'FALSE_POSITIVE') AS false_positives
        FROM cases
        GROUP BY analyst
        ORDER BY assigned_cases DESC
        LIMIT 12
    """)
    rows = cursor.fetchall()
    conn.close()
    return [
        AnalystPerformanceResponse(
            analyst=r[0],
            assigned_cases=r[1],
            resolved_cases=r[2],
            confirmed_fraud=r[3],
            false_positives=r[4],
        )
        for r in rows
    ]


@app.get("/analytics/heat-map", response_model=list[FraudHeatMapPointResponse])
def analytics_heat_map(current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    prepare_analytics_tables(cursor)
    conn.commit()
    cursor.execute("""
        SELECT
            COALESCE(NULLIF(e.location, ''), 'Unknown') AS location,
            COUNT(DISTINCT f.id) AS alerts,
            COALESCE(AVG(f.risk_score), 0) AS average_risk,
            COALESCE(MAX(f.risk_level), 'LOW') AS highest_risk
        FROM fraud_alerts f
        LEFT JOIN events e ON e.user_id = f.user_id
        GROUP BY location
        ORDER BY alerts DESC, average_risk DESC
        LIMIT 16
    """)
    rows = cursor.fetchall()
    conn.close()
    return [
        FraudHeatMapPointResponse(location=r[0], alerts=r[1], average_risk=round(float(r[2]), 1), highest_risk=r[3])
        for r in rows
    ]


@app.get("/export/fraud-alerts.csv")
def export_fraud_alerts(current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    prepare_analytics_tables(cursor)
    conn.commit()
    cursor.execute("""
        SELECT user_id, risk_score, risk_level, recommended_action, confidence, timestamp
        FROM fraud_alerts
        ORDER BY timestamp DESC NULLS LAST, id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return csv_response("fraud-alerts.csv", ["user_id", "risk_score", "risk_level", "action", "confidence", "time"], rows)


@app.get("/export/cases.csv")
def export_cases(current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    prepare_analytics_tables(cursor)
    conn.commit()
    cursor.execute("""
        SELECT case_number, user_id, risk_score, risk_level, status, priority, assigned_to, analyst_feedback, decision, potential_loss, actual_loss, created_at, updated_at
        FROM cases
        ORDER BY updated_at DESC, id DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return csv_response(
        "cases.csv",
        ["case_number", "user_id", "risk_score", "risk_level", "status", "priority", "assigned_to", "analyst_feedback", "decision", "potential_loss", "actual_loss", "created_at", "updated_at"],
        rows,
    )


@app.get("/export/monthly-report.csv")
def export_monthly_report(current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    prepare_analytics_tables(cursor)
    conn.commit()
    cursor.execute("""
        SELECT
            COALESCE(DATE_TRUNC('month', created_at)::DATE::TEXT, 'Unknown') AS month,
            COUNT(*) AS cases,
            COUNT(*) FILTER (WHERE analyst_feedback = 'TRUE_FRAUD') AS confirmed_fraud,
            COUNT(*) FILTER (WHERE analyst_feedback = 'FALSE_POSITIVE') AS false_positives,
            COUNT(*) FILTER (WHERE status IN ('RESOLVED', 'ARCHIVED')) AS resolved
        FROM cases
        GROUP BY month
        ORDER BY month DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return csv_response("monthly-report.csv", ["month", "cases", "confirmed_fraud", "false_positives", "resolved"], rows)


@app.get("/reports/monthly.pdf")
def monthly_pdf_report(current_user: AuthUserResponse = Depends(get_current_user)):
    overview = analytics_overview(current_user)
    heat = analytics_heat_map(current_user)[:5]
    lines = [
        "Boujuron Intelligence Monthly Fraud Report",
        f"Generated for: {current_user.name} ({current_user.role})",
        "",
        f"Events Analyzed: {overview.total_events:,}",
        f"Fraud Alerts: {overview.fraud_alerts:,}",
        f"Confirmed Fraud Cases: {overview.confirmed_fraud_cases:,}",
        f"Fraud Prevention Rate: {overview.fraud_prevention_rate}%",
        f"False Positive Rate: {overview.false_positive_rate}%",
        f"Average Investigation Time: {overview.average_investigation_minutes} minutes",
        f"Cases Resolved: {overview.cases_resolved:,}",
        "",
        "Top Attack Locations:",
        *[f"- {item.location}: {item.alerts} alerts, avg risk {item.average_risk}" for item in heat],
        "",
        "Recommendations:",
        "- Review critical-risk locations and anonymous-network activity.",
        "- Prioritize cases with confirmed fraud feedback for model retraining.",
        "- Track false positives weekly to improve analyst workload quality.",
    ]
    return Response(
        content=simple_pdf("Boujuron Intelligence", lines),
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="monthly-fraud-report.pdf"'},
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
