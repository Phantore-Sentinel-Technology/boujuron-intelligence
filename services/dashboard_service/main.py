import asyncio
import base64
import csv
import hashlib
import hmac
import io
import json
import os
import secrets
import smtplib
import time
import urllib.request
from collections import Counter
from datetime import datetime, timedelta
from statistics import mean

import psycopg2
from psycopg2.extras import Json
from fastapi import Depends, FastAPI, Header, HTTPException, Query, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from config.settings import settings
from services.dashboard_service.schemas import (
    AuthLoginRequest,
    AuthRegisterRequest,
    AuthTokenResponse,
    AuthUserResponse,
    ApiKeyCreateRequest,
    ApiKeyResponse,
    ApiKeyUsageResponse,
    AlertDestinationRequest,
    AlertDestinationResponse,
    BehaviorEvaluationResponse,
    BehaviorSettingsResponse,
    BehaviorSettingsUpdate,
    AccountSecurityResponse,
    AnalystPerformanceResponse,
    AnalyticsOverviewResponse,
    AuditLogResponse,
    CaseActionRequest,
    CaseActionResponse,
    CaseDetailResponse,
    CaseNoteRequest,
    CaseNoteResponse,
    CaseSummaryResponse,
    CaseTimelineResponse,
    CaseUpdateRequest,
    DemoFraudEventRequest,
    DeviceProfileResponse,
    DeviceTrustUpdate,
    DecisionRuleRequest,
    DecisionRuleResponse,
    EventResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    InviteCreateRequest,
    InviteResponse,
    FraudAlertResponse,
    BehaviorAnomaly,
    FraudHeatMapPointResponse,
    EvidenceEdge,
    EvidenceGraphResponse,
    EvidenceNode,
    InvoiceResponse,
    IntelligenceActivityResponse,
    InvestigationFeedItemResponse,
    NotificationResponse,
    OrganizationCreateRequest,
    OrganizationResponse,
    ConsortiumSettingsResponse,
    ConsortiumSettingsUpdate,
    RiskTimelinePoint,
    RiskDistributionResponse,
    RiskScoreRequest,
    RiskScoreResponse,
    ResetPasswordRequest,
    ScoreBreakdownItem,
    TrendPointResponse,
    UserProfileEvent,
    UserProfileResponse,
)
from services.risk_engine_service.engine import analyze_event
from pathlib import Path
app = FastAPI(title="Boujuron Dashboard API")

clients = []
FRONTEND_DIST = Path("frontend/dist")
AUTH_SECRET = settings.JWT_SECRET
TOKEN_TTL_SECONDS = 60 * 60 * 12
PASSWORD_RESET_TTL_MINUTES = 60
ALLOWED_ROLES = {"Admin", "Fraud Analyst", "Investigator", "Read-Only Auditor"}
CASE_STATUSES = {
    "NEW", "ASSIGNED", "INVESTIGATING", "ESCALATED", "RESOLVED", "ARCHIVED",
    "OPEN", "UNDER_REVIEW", "CONFIRMED_FRAUD", "FALSE_POSITIVE", "REVERSED", "CLOSED",
}
CASE_PRIORITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
ANALYST_FEEDBACK = {"TRUE_FRAUD", "FALSE_POSITIVE", "NEEDS_REVIEW"}
CASE_DECISIONS = {"ALLOW", "VERIFY", "BLOCK", "FREEZE", "ESCALATE", "STEP_UP_VERIFY", "HOLD_FOR_REVIEW", "PND_OR_BLOCK"}


def get_cors_origins():
    configured_origins = [
        origin.strip()
        for origin in settings.CORS_ORIGINS.split(",")
        if origin.strip()
    ]
    fallback_origins = [
        settings.FRONTEND_URL,
        "https://boujuron.netlify.app",
        "http://localhost:5173",
        "http://localhost:4173",
        "http://localhost:8002",
    ]
    return sorted({origin.rstrip("/") for origin in configured_origins + fallback_origins if origin})

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_origin_regex=r"https://.*\.netlify\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if (FRONTEND_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

def get_db():
    conn = psycopg2.connect(settings.DATABASE_URL)
    return conn, conn.cursor()


def ensure_organization_tables(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS organizations (
            id SERIAL PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            slug TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        INSERT INTO organizations (name, slug)
        VALUES ('Boujuron', 'boujuron')
        ON CONFLICT (slug) DO NOTHING
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS organization_risk_settings (
            organization_id INTEGER PRIMARY KEY,
            amount_spike_multiplier NUMERIC DEFAULT 5,
            minimum_amount_delta NUMERIC DEFAULT 100000,
            new_device_points INTEGER DEFAULT 25,
            new_location_points INTEGER DEFAULT 20,
            unusual_hour_points INTEGER DEFAULT 20,
            velocity_window_minutes INTEGER DEFAULT 10,
            transaction_velocity_limit INTEGER DEFAULT 5,
            login_velocity_limit INTEGER DEFAULT 8,
            velocity_points INTEGER DEFAULT 30,
            minimum_profile_events INTEGER DEFAULT 3,
            adaptive_learning_enabled BOOLEAN DEFAULT TRUE,
            trusted_learning_max_score INTEGER DEFAULT 39,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        INSERT INTO organization_risk_settings (organization_id)
        SELECT id FROM organizations WHERE slug = 'boujuron'
        ON CONFLICT (organization_id) DO NOTHING
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS behavioral_profiles (
            organization_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            event_count INTEGER DEFAULT 0,
            trusted_event_count INTEGER DEFAULT 0,
            amount_count INTEGER DEFAULT 0,
            amount_mean NUMERIC DEFAULT 0,
            amount_m2 NUMERIC DEFAULT 0,
            known_devices JSONB DEFAULT '[]'::jsonb,
            known_locations JSONB DEFAULT '[]'::jsonb,
            hour_histogram JSONB DEFAULT '{}'::jsonb,
            first_seen_at TIMESTAMP,
            last_seen_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (organization_id, user_id)
        )
    """)


def ensure_device_security_tables(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS device_fingerprints (
            organization_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            fingerprint TEXT NOT NULL,
            label TEXT DEFAULT '',
            status TEXT DEFAULT 'NEW',
            trust_score INTEGER DEFAULT 25,
            first_seen_at TIMESTAMP NOT NULL,
            last_seen_at TIMESTAMP NOT NULL,
            event_count INTEGER DEFAULT 1,
            last_ip TEXT,
            last_location TEXT,
            platform TEXT,
            operating_system TEXT,
            browser TEXT,
            user_agent TEXT,
            integrity_flags JSONB DEFAULT '[]'::jsonb,
            metadata JSONB DEFAULT '{}'::jsonb,
            PRIMARY KEY (organization_id, user_id, fingerprint)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS account_security_state (
            organization_id INTEGER NOT NULL,
            user_id TEXT NOT NULL,
            password_changed_at TIMESTAMP,
            sim_changed_at TIMESTAMP,
            last_successful_login_at TIMESTAMP,
            last_login_fingerprint TEXT,
            last_login_ip TEXT,
            last_login_location TEXT,
            failed_login_count INTEGER DEFAULT 0,
            failed_login_window_started_at TIMESTAMP,
            takeover_risk INTEGER DEFAULT 0,
            takeover_level TEXT DEFAULT 'LOW',
            recommendation TEXT DEFAULT 'ALLOW',
            indicators JSONB DEFAULT '[]'::jsonb,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (organization_id, user_id)
        )
    """)


def default_organization_id(cursor) -> int:
    ensure_organization_tables(cursor)
    cursor.execute("SELECT id FROM organizations WHERE slug = 'boujuron'")
    return cursor.fetchone()[0]


def ensure_auth_tables(cursor):
    ensure_organization_tables(cursor)
    organization_id = default_organization_id(cursor)
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
    cursor.execute("ALTER TABLE app_users ADD COLUMN IF NOT EXISTS organization_id INTEGER")
    cursor.execute("UPDATE app_users SET organization_id = %s WHERE organization_id IS NULL", (organization_id,))
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES app_users(id) ON DELETE CASCADE,
            token TEXT UNIQUE NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invite_tokens (
            id SERIAL PRIMARY KEY,
            token TEXT UNIQUE NOT NULL,
            email TEXT NOT NULL,
            role TEXT NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            used_at TIMESTAMP,
            used_by INTEGER REFERENCES app_users(id) ON DELETE SET NULL,
            created_by INTEGER REFERENCES app_users(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("ALTER TABLE invite_tokens ADD COLUMN IF NOT EXISTS organization_id INTEGER")
    cursor.execute("UPDATE invite_tokens SET organization_id = %s WHERE organization_id IS NULL", (organization_id,))
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS client_api_keys (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            key_prefix TEXT NOT NULL,
            key_hash TEXT UNIQUE NOT NULL,
            active BOOLEAN DEFAULT TRUE,
            last_used_at TIMESTAMP,
            created_by INTEGER REFERENCES app_users(id) ON DELETE SET NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("ALTER TABLE client_api_keys ADD COLUMN IF NOT EXISTS organization_id INTEGER")
    cursor.execute("ALTER TABLE client_api_keys ADD COLUMN IF NOT EXISTS request_count BIGINT DEFAULT 0")
    cursor.execute("ALTER TABLE client_api_keys ADD COLUMN IF NOT EXISTS rotated_from INTEGER")
    cursor.execute("UPDATE client_api_keys SET organization_id = %s WHERE organization_id IS NULL", (organization_id,))
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id SERIAL PRIMARY KEY,
            organization_id INTEGER NOT NULL,
            invoice_number TEXT UNIQUE NOT NULL,
            period TEXT NOT NULL,
            amount NUMERIC DEFAULT 0,
            currency TEXT DEFAULT 'USD',
            status TEXT DEFAULT 'DRAFT',
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
        ("organization_id", "INTEGER"),
        ("transaction_id", "TEXT"),
        ("transaction_direction", "TEXT DEFAULT 'DEBIT'"),
        ("amount", "NUMERIC"),
        ("location", "TEXT"),
        ("network", "TEXT"),
        ("device_id", "TEXT"),
        ("metadata", "JSONB"),
        ("source", "TEXT"),
    ):
        cursor.execute(f"""
            ALTER TABLE events
            ADD COLUMN IF NOT EXISTS {column_name} {column_type}
        """)
    cursor.execute("""
        UPDATE events
        SET organization_id = (SELECT id FROM organizations WHERE slug = 'boujuron')
        WHERE organization_id IS NULL
    """)


def ensure_risk_decision_table(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS risk_decisions (
            id SERIAL PRIMARY KEY,
            transaction_id TEXT NOT NULL,
            idempotency_key TEXT UNIQUE,
            user_id TEXT NOT NULL,
            risk_score INTEGER NOT NULL,
            risk_level TEXT NOT NULL,
            action TEXT NOT NULL,
            recommendation TEXT NOT NULL,
            confidence NUMERIC,
            reasons JSONB DEFAULT '[]'::jsonb,
            signals JSONB DEFAULT '[]'::jsonb,
            behavioral_match BOOLEAN,
            request_payload JSONB DEFAULT '{}'::jsonb,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    for column_name, column_type in (
        ("organization_id", "INTEGER"),
        ("transaction_direction", "TEXT DEFAULT 'DEBIT'"),
        ("recommendation", "TEXT"),
        ("analyst_feedback", "TEXT"),
        ("feedback_at", "TIMESTAMP"),
        ("learned", "BOOLEAN DEFAULT FALSE"),
        ("device_intelligence", "JSONB"),
        ("account_takeover", "JSONB"),
        ("action_decision_id", "INTEGER"),
        ("matched_rules", "JSONB DEFAULT '[]'::jsonb"),
    ):
        cursor.execute(f"""
            ALTER TABLE risk_decisions
            ADD COLUMN IF NOT EXISTS {column_name} {column_type}
        """)
    cursor.execute("ALTER TABLE risk_decisions DROP CONSTRAINT IF EXISTS risk_decisions_idempotency_key_key")
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS risk_decisions_org_idempotency_key
        ON risk_decisions (organization_id, idempotency_key)
        WHERE idempotency_key IS NOT NULL
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
    cursor.execute("ALTER TABLE cases ADD COLUMN IF NOT EXISTS organization_id INTEGER")
    for column_name, column_type in (
        ("transaction_id", "TEXT"),
        ("transaction_direction", "TEXT DEFAULT 'DEBIT'"),
        ("confidence", "NUMERIC"),
        ("analyst_note", "TEXT"),
        ("reversed_at", "TIMESTAMP"),
    ):
        cursor.execute(f"""
            ALTER TABLE cases
            ADD COLUMN IF NOT EXISTS {column_name} {column_type}
        """)
    cursor.execute("""
        UPDATE cases
        SET organization_id = (SELECT id FROM organizations WHERE slug = 'boujuron')
        WHERE organization_id IS NULL
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
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fraud_audit_logs (
            id SERIAL PRIMARY KEY,
            organization_id INTEGER,
            case_id INTEGER,
            transaction_id TEXT,
            user_id TEXT,
            action_taken TEXT NOT NULL,
            previous_status TEXT,
            new_status TEXT,
            analyst_note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def ensure_decision_rule_tables(cursor):
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS decision_rules (
            id SERIAL PRIMARY KEY,
            organization_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            conditions JSONB NOT NULL DEFAULT '[]'::jsonb,
            action TEXT NOT NULL,
            score_adjustment INTEGER DEFAULT 0,
            priority INTEGER DEFAULT 100,
            enabled BOOLEAN DEFAULT TRUE,
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (organization_id, name)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS action_decisions (
            id SERIAL PRIMARY KEY,
            organization_id INTEGER NOT NULL,
            risk_decision_id INTEGER,
            transaction_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            model_action TEXT NOT NULL,
            final_action TEXT NOT NULL,
            matched_rules JSONB DEFAULT '[]'::jsonb,
            status TEXT DEFAULT 'DECIDED',
            reason TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback_learning_events (
            id SERIAL PRIMARY KEY,
            organization_id INTEGER NOT NULL,
            risk_decision_id INTEGER NOT NULL,
            feedback TEXT NOT NULL,
            learned_features JSONB DEFAULT '[]'::jsonb,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (risk_decision_id, feedback)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS alert_destinations (
            id SERIAL PRIMARY KEY,
            organization_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            channel TEXT NOT NULL,
            target TEXT NOT NULL,
            minimum_risk TEXT DEFAULT 'HIGH',
            enabled BOOLEAN DEFAULT TRUE,
            last_status TEXT,
            last_sent_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consortium_settings (
            organization_id INTEGER PRIMARY KEY,
            enabled BOOLEAN DEFAULT FALSE,
            share_devices BOOLEAN DEFAULT TRUE,
            share_ips BOOLEAN DEFAULT TRUE,
            share_emails BOOLEAN DEFAULT FALSE,
            share_phones BOOLEAN DEFAULT FALSE,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consortium_reputation (
            entity_type TEXT NOT NULL,
            entity_hash TEXT NOT NULL,
            organization_id INTEGER NOT NULL,
            confirmed_fraud_count INTEGER DEFAULT 0,
            false_positive_count INTEGER DEFAULT 0,
            last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (entity_type, entity_hash, organization_id)
        )
    """)


def ensure_fraud_alert_columns(cursor):
    for column_name, column_type in (
        ("organization_id", "INTEGER"),
        ("risk_decision_id", "INTEGER"),
        ("transaction_id", "TEXT"),
        ("transaction_direction", "TEXT DEFAULT 'DEBIT'"),
        ("recommended_action", "TEXT"),
        ("confidence", "NUMERIC"),
        ("signals_triggered", "INTEGER"),
        ("behavioral_match", "BOOLEAN"),
    ):
        cursor.execute(f"""
            ALTER TABLE fraud_alerts
            ADD COLUMN IF NOT EXISTS {column_name} {column_type}
        """)
    cursor.execute("""
        UPDATE fraud_alerts
        SET organization_id = (SELECT id FROM organizations WHERE slug = 'boujuron')
        WHERE organization_id IS NULL
    """)


def prepare_analytics_tables(cursor):
    ensure_organization_tables(cursor)
    ensure_device_security_tables(cursor)
    ensure_event_table(cursor)
    ensure_fraud_alert_table(cursor)
    ensure_case_tables(cursor)
    ensure_risk_decision_table(cursor)
    ensure_decision_rule_tables(cursor)


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


def recommended_action_from_risk(risk_level: str | None) -> str:
    return {
        "LOW": "ALLOW",
        "MEDIUM": "STEP_UP_VERIFY",
        "HIGH": "HOLD_FOR_REVIEW",
        "CRITICAL": "PND_OR_BLOCK",
    }.get((risk_level or "LOW").upper(), "REVIEW")


def should_create_case(risk_level: str | None, action: str | None) -> bool:
    normalized_level = (risk_level or "LOW").upper()
    normalized_action = (action or "").upper()
    return normalized_level in {"HIGH", "CRITICAL"} or normalized_action in {"HOLD_FOR_REVIEW", "PND_OR_BLOCK"}


def audit_log(
    cursor,
    organization_id: int,
    case_id: int | None,
    transaction_id: str | None,
    user_id: str | None,
    action_taken: str,
    previous_status: str | None = None,
    new_status: str | None = None,
    analyst_note: str | None = None,
):
    cursor.execute("""
        INSERT INTO fraud_audit_logs (
            organization_id, case_id, transaction_id, user_id, action_taken,
            previous_status, new_status, analyst_note
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        organization_id,
        case_id,
        transaction_id,
        user_id,
        action_taken,
        previous_status,
        new_status,
        analyst_note,
    ))


def materialize_cases_from_alerts(cursor, organization_id: int | None = None):
    ensure_fraud_alert_table(cursor)
    ensure_case_tables(cursor)
    cursor.execute("""
        UPDATE cases c
        SET organization_id = f.organization_id
        FROM fraud_alerts f
        WHERE c.fraud_alert_id = f.id AND c.organization_id IS NULL
    """)
    cursor.execute("""
        SELECT
            id,
            organization_id,
            user_id,
            reason,
            risk_score,
            risk_level,
            recommended_action,
            confidence,
            transaction_id,
            transaction_direction,
            timestamp
        FROM fraud_alerts
        WHERE (%s IS NULL OR organization_id = %s)
          AND (risk_level IN ('HIGH', 'CRITICAL') OR recommended_action IN ('HOLD_FOR_REVIEW', 'PND_OR_BLOCK'))
        ORDER BY id ASC
    """, (organization_id, organization_id))
    alerts = cursor.fetchall()
    for alert in alerts:
        (
            alert_id, alert_organization_id, user_id, reason, risk_score, risk_level,
            recommended_action, confidence, transaction_id, transaction_direction, timestamp
        ) = alert
        cursor.execute("SELECT id FROM cases WHERE fraud_alert_id = %s", (alert_id,))
        if cursor.fetchone():
            continue
        action = recommended_action or recommended_action_from_risk(risk_level)
        if not should_create_case(risk_level, action):
            continue

        cursor.execute("""
            INSERT INTO cases (
                case_number,
                organization_id,
                fraud_alert_id,
                user_id,
                transaction_id,
                transaction_direction,
                reason,
                risk_score,
                risk_level,
                confidence,
                status,
                priority,
                recommended_action,
                created_at,
                updated_at
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, COALESCE(%s, CURRENT_TIMESTAMP), CURRENT_TIMESTAMP)
            RETURNING id
        """, (
            f"CASE-{alert_id:04d}",
            alert_organization_id,
            alert_id,
            user_id,
            transaction_id,
            transaction_direction or "DEBIT",
            reason or "",
            int(risk_score or 0),
            risk_level or "LOW",
            float(confidence or 0),
            "OPEN",
            priority_from_risk(risk_level),
            action,
            timestamp,
        ))
        case_id = cursor.fetchone()[0]
        cursor.execute("""
            INSERT INTO case_timeline (case_id, event_type, description, actor)
            VALUES (%s, %s, %s, %s)
        """, (case_id, "CASE_CREATED", "Case opened from fraud alert", "System"))
        audit_log(
            cursor,
            int(alert_organization_id),
            case_id,
            transaction_id,
            user_id,
            "CASE_CREATED",
            None,
            "OPEN",
            "Case opened for banking fraud review",
        )
        if action == "HOLD_FOR_REVIEW":
            audit_log(cursor, int(alert_organization_id), case_id, transaction_id, user_id, "TRANSACTION_HELD", None, "OPEN")
        elif action == "PND_OR_BLOCK":
            audit_log(cursor, int(alert_organization_id), case_id, transaction_id, user_id, "TRANSACTION_BLOCKED", None, "OPEN")


def auto_close_high_risk_cases(cursor, organization_id: int | None = None):
    return


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
        transaction_id=row[3],
        transaction_direction=row[4],
        risk_score=row[5],
        risk_level=row[6],
        confidence=float(row[7]) if row[7] is not None else None,
        recommended_action=row[8],
        status=row[9],
        priority=row[10],
        assigned_to=row[11],
        analyst_feedback=row[12],
        created_at=str(row[13]),
        updated_at=str(row[14]),
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


def create_invite_token() -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    groups = ["".join(secrets.choice(alphabet) for _ in range(4)) for _ in range(3)]
    return f"BJRN-{'-'.join(groups)}"


def invite_url(token: str) -> str:
    base_url = settings.FRONTEND_URL.rstrip("/")
    for suffix in ("/login", "/register"):
        if base_url.endswith(suffix):
            base_url = base_url[: -len(suffix)]
    return f"{base_url}/register?invite={token}"


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
    cursor.execute("SELECT id, name, email, role, organization_id FROM app_users WHERE id = %s", (payload["uid"],))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=401, detail="User no longer exists")
    return AuthUserResponse(id=row[0], name=row[1], email=row[2], role=row[3], organization_id=row[4])


def require_admin(current_user: AuthUserResponse):
    if current_user.role != "Admin":
        raise HTTPException(status_code=403, detail="Admin access required")


def hash_api_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def authenticate_risk_client(
    authorization: str | None = Header(default=None),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    if x_api_key:
        conn, cursor = get_db()
        ensure_auth_tables(cursor)
        cursor.execute("""
        SELECT id, name, key_prefix, organization_id
            FROM client_api_keys
            WHERE key_hash = %s AND active = TRUE
        """, (hash_api_key(x_api_key.strip()),))
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=401, detail="Invalid API key")
        cursor.execute("""
            UPDATE client_api_keys
            SET last_used_at = CURRENT_TIMESTAMP, request_count = request_count + 1
            WHERE id = %s
        """, (row[0],))
        conn.commit()
        conn.close()
        return {"type": "api_key", "id": row[0], "name": row[1], "prefix": row[2], "organization_id": row[3]}

    user = get_current_user(authorization)
    return {
        "type": "user",
        "id": user.id,
        "name": user.name,
        "role": user.role,
        "organization_id": user.organization_id,
    }


async def broadcast_alert(alert: dict, organization_id: int):
    disconnected = []
    for connection in clients:
        if connection["organization_id"] != organization_id:
            continue
        try:
            await connection["websocket"].send_json(alert)
        except Exception:
            disconnected.append(connection)
    for connection in disconnected:
        if connection in clients:
            clients.remove(connection)


def api_key_response(row, api_key: str | None = None) -> ApiKeyResponse:
    key_id, name, key_prefix, active, request_count, last_used_at, created_at = row
    return ApiKeyResponse(
        id=key_id,
        name=name,
        key_prefix=key_prefix,
        api_key=api_key,
        active=active,
        request_count=int(request_count or 0),
        last_used_at=str(last_used_at) if last_used_at else None,
        created_at=str(created_at),
    )


def behavior_settings(cursor, organization_id: int) -> dict:
    ensure_organization_tables(cursor)
    cursor.execute("""
        INSERT INTO organization_risk_settings (organization_id)
        VALUES (%s)
        ON CONFLICT (organization_id) DO NOTHING
    """, (organization_id,))
    cursor.execute("""
        SELECT
            amount_spike_multiplier,
            minimum_amount_delta,
            new_device_points,
            new_location_points,
            unusual_hour_points,
            velocity_window_minutes,
            transaction_velocity_limit,
            login_velocity_limit,
            velocity_points,
            minimum_profile_events,
            adaptive_learning_enabled,
            trusted_learning_max_score
        FROM organization_risk_settings
        WHERE organization_id = %s
    """, (organization_id,))
    row = cursor.fetchone()
    keys = (
        "amount_spike_multiplier",
        "minimum_amount_delta",
        "new_device_points",
        "new_location_points",
        "unusual_hour_points",
        "velocity_window_minutes",
        "transaction_velocity_limit",
        "login_velocity_limit",
        "velocity_points",
        "minimum_profile_events",
        "adaptive_learning_enabled",
        "trusted_learning_max_score",
    )
    values = dict(zip(keys, row))
    values["amount_spike_multiplier"] = float(values["amount_spike_multiplier"])
    values["minimum_amount_delta"] = float(values["minimum_amount_delta"])
    return values


def usual_hours(hour_histogram: dict) -> tuple[int | None, int | None]:
    populated = sorted(int(hour) for hour, count in hour_histogram.items() if int(count) > 0)
    if not populated:
        return None, None
    weighted_total = sum(int(hour) * int(hour_histogram[str(hour)]) for hour in populated)
    count = sum(int(hour_histogram[str(hour)]) for hour in populated)
    center = round(weighted_total / count)
    return max(center - 3, 0), min(center + 3, 23)


def event_datetime(value: str) -> datetime:
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=None)


def device_fingerprint(event: dict) -> str:
    device_id = str(event.get("device_id") or "").strip().lower()
    if device_id:
        return hashlib.sha256(f"device-id|{device_id}".encode("utf-8")).hexdigest()[:32]
    stable_parts = [
        event.get("platform"),
        event.get("operating_system"),
        event.get("browser"),
        event.get("user_agent"),
        event.get("screen_resolution"),
        event.get("timezone"),
        event.get("language"),
        event.get("app_version"),
        event.get("device_type") or event.get("device"),
    ]
    canonical = "|".join(str(part or "").strip().lower() for part in stable_parts)
    if not canonical.replace("|", ""):
        canonical = f"unknown|{event.get('ip', '')}"
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]


def device_integrity_flags(event: dict) -> list[str]:
    flags = []
    if event.get("is_rooted"):
        flags.append("ROOTED")
    if event.get("is_emulator"):
        flags.append("EMULATOR")
    if event.get("browser_tampering"):
        flags.append("BROWSER_TAMPERING")
    attestation = str(event.get("device_attestation") or "").upper()
    if attestation in {"FAILED", "INVALID", "UNTRUSTED"}:
        flags.append("ATTESTATION_FAILED")
    network = str(event.get("network") or "").upper()
    if network in {"VPN", "TOR", "PROXY"}:
        flags.append(network)
    return flags


def load_device_intelligence(cursor, organization_id: int, user_id: str, event: dict) -> dict:
    fingerprint = device_fingerprint(event)
    cursor.execute("""
        SELECT status, trust_score, first_seen_at, last_seen_at, event_count, integrity_flags
        FROM device_fingerprints
        WHERE organization_id = %s AND user_id = %s AND fingerprint = %s
    """, (organization_id, user_id, fingerprint))
    row = cursor.fetchone()
    timestamp = event_datetime(event["timestamp"])
    flags = sorted(set(device_integrity_flags(event) + (list(row[5] or []) if row else [])))
    return {
        "fingerprint": fingerprint,
        "status": row[0] if row else "NEW",
        "trust_score": int(row[1] or 0) if row else 25,
        "is_new_device": row is None,
        "first_seen_at": str(row[2] if row else timestamp),
        "last_seen_at": str(timestamp),
        "event_count": int(row[4] or 0) + 1 if row else 1,
        "integrity_flags": flags,
    }


def load_account_takeover_context(
    cursor,
    organization_id: int,
    user_id: str,
    event: dict,
    device_data: dict,
) -> dict:
    cursor.execute("""
        SELECT password_changed_at, sim_changed_at, last_successful_login_at,
               last_login_fingerprint, last_login_ip, last_login_location,
               failed_login_count, failed_login_window_started_at
        FROM account_security_state
        WHERE organization_id = %s AND user_id = %s
    """, (organization_id, user_id))
    row = cursor.fetchone()
    now = event_datetime(event["timestamp"])
    password_changed_at = row[0] if row else None
    sim_changed_at = row[1] if row else None
    last_login_at = row[2] if row else None
    last_fingerprint = row[3] if row else None
    last_ip = row[4] if row else None
    last_location = row[5] if row else None
    stored_failures = int(row[6] or 0) if row else 0
    failed_window = row[7] if row else None

    event_type = str(event.get("event_type") or "").lower()
    password_recent = bool(event.get("password_changed_recently"))
    if password_changed_at and now - password_changed_at <= timedelta(hours=24):
        password_recent = True
    sim_recent = bool(event.get("sim_swap_detected"))
    if sim_changed_at and now - sim_changed_at <= timedelta(hours=72):
        sim_recent = True

    failures = max(stored_failures, int(event.get("failed_login_count") or 0))
    if failed_window and now - failed_window > timedelta(minutes=30):
        failures = int(event.get("failed_login_count") or 0)
        failed_window = None

    correlated_signals = []
    if device_data["is_new_device"] and password_recent:
        correlated_signals.append({
            "category": "ACCOUNT_TAKEOVER",
            "label": "New device after password change",
            "points": 35,
            "evidence": "A previously unseen device appeared within 24 hours of a password change",
        })
    if device_data["is_new_device"] and sim_recent:
        correlated_signals.append({
            "category": "ACCOUNT_TAKEOVER",
            "label": "New device after SIM change",
            "points": 55,
            "evidence": "A previously unseen device appeared within 72 hours of a SIM change",
        })
    if event_type in {"login", "login_success"} and failures >= 5:
        correlated_signals.append({
            "category": "ACCOUNT_TAKEOVER",
            "label": "Successful login after failure burst",
            "points": 45,
            "evidence": f"Successful authentication followed {failures} recent failed attempts",
        })
    if (
        event_type in {"login", "login_success"}
        and last_login_at
        and now - last_login_at <= timedelta(minutes=30)
        and last_fingerprint
        and last_fingerprint != device_data["fingerprint"]
    ):
        correlated_signals.append({
            "category": "ACCOUNT_TAKEOVER",
            "label": "Rapid device switching",
            "points": 30,
            "evidence": "The account authenticated from different device fingerprints within 30 minutes",
        })
    current_location = str(event.get("location") or "").strip().lower()
    if (
        event_type in {"login", "login_success"}
        and last_login_at
        and now - last_login_at <= timedelta(minutes=30)
        and last_location
        and current_location
        and last_location.lower() != current_location
    ):
        correlated_signals.append({
            "category": "ACCOUNT_TAKEOVER",
            "label": "Rapid location change",
            "points": 30,
            "evidence": f"Login location changed from {last_location} to {event.get('location')} within 30 minutes",
        })
    if last_ip and event.get("ip") and last_ip != event["ip"] and device_data["is_new_device"]:
        correlated_signals.append({
            "category": "ACCOUNT_TAKEOVER",
            "label": "New device and network identity",
            "points": 20,
            "evidence": "Both device fingerprint and IP address changed from the previous login",
        })

    return {
        "signals": correlated_signals,
        "password_changed_at": password_changed_at,
        "sim_changed_at": sim_changed_at,
        "last_successful_login_at": last_login_at,
        "last_login_fingerprint": last_fingerprint,
        "last_login_ip": last_ip,
        "last_login_location": last_location,
        "failed_login_count": failures,
        "failed_login_window_started_at": failed_window,
    }


def persist_device_intelligence(
    cursor,
    organization_id: int,
    user_id: str,
    event: dict,
    device_data: dict,
    risk_result: dict,
):
    flags = device_data["integrity_flags"]
    prior_status = device_data["status"]
    event_count = device_data["event_count"]
    if risk_result["account_takeover"]["detected"] or risk_result["risk_score"] >= 90:
        status = "BLOCKED"
        trust_score = 0
    elif flags or risk_result["risk_score"] >= 70:
        status = "SUSPICIOUS"
        trust_score = min(device_data["trust_score"], 20)
    elif prior_status == "TRUSTED" or (event_count >= 2 and risk_result["risk_score"] < 40):
        status = "TRUSTED"
        trust_score = min(100, max(device_data["trust_score"], 60) + 5)
    else:
        status = "NEW"
        trust_score = max(device_data["trust_score"], 25)

    device_data["status"] = status
    device_data["trust_score"] = trust_score
    cursor.execute("""
        INSERT INTO device_fingerprints (
            organization_id, user_id, fingerprint, label, status, trust_score,
            first_seen_at, last_seen_at, event_count, last_ip, last_location,
            platform, operating_system, browser, user_agent, integrity_flags, metadata
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (organization_id, user_id, fingerprint) DO UPDATE SET
            label = EXCLUDED.label,
            status = EXCLUDED.status,
            trust_score = EXCLUDED.trust_score,
            last_seen_at = EXCLUDED.last_seen_at,
            event_count = device_fingerprints.event_count + 1,
            last_ip = EXCLUDED.last_ip,
            last_location = EXCLUDED.last_location,
            platform = EXCLUDED.platform,
            operating_system = EXCLUDED.operating_system,
            browser = EXCLUDED.browser,
            user_agent = EXCLUDED.user_agent,
            integrity_flags = EXCLUDED.integrity_flags,
            metadata = EXCLUDED.metadata
    """, (
        organization_id,
        user_id,
        device_data["fingerprint"],
        event.get("device_id") or event.get("device_type") or event.get("device") or "Unknown device",
        status,
        trust_score,
        event_datetime(device_data["first_seen_at"]),
        event_datetime(event["timestamp"]),
        1,
        event.get("ip"),
        event.get("location"),
        event.get("platform"),
        event.get("operating_system"),
        event.get("browser"),
        event.get("user_agent"),
        Json(flags),
        Json(event.get("metadata") or {}),
    ))


def persist_account_security_state(
    cursor,
    organization_id: int,
    user_id: str,
    event: dict,
    device_data: dict,
    takeover: dict,
    context: dict,
):
    now = event_datetime(event["timestamp"])
    event_type = str(event.get("event_type") or "").lower()
    password_at = now if event_type in {"password_change", "password_reset"} or event.get("password_changed_recently") else context["password_changed_at"]
    sim_at = now if event_type == "sim_swap" or event.get("sim_swap_detected") else context["sim_changed_at"]
    failed_count = context["failed_login_count"]
    failed_window = context["failed_login_window_started_at"]
    if event_type in {"login_failure", "multiple_failed_logins"}:
        failed_count = max(failed_count + 1, int(event.get("failed_login_count") or 0))
        failed_window = now
    elif event_type in {"login", "login_success"}:
        failed_count = 0

    successful_login = event_type in {"login", "login_success"}
    cursor.execute("""
        INSERT INTO account_security_state (
            organization_id, user_id, password_changed_at, sim_changed_at,
            last_successful_login_at, last_login_fingerprint, last_login_ip,
            last_login_location, failed_login_count, failed_login_window_started_at,
            takeover_risk, takeover_level, recommendation, indicators, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (organization_id, user_id) DO UPDATE SET
            password_changed_at = EXCLUDED.password_changed_at,
            sim_changed_at = EXCLUDED.sim_changed_at,
            last_successful_login_at = COALESCE(EXCLUDED.last_successful_login_at, account_security_state.last_successful_login_at),
            last_login_fingerprint = COALESCE(EXCLUDED.last_login_fingerprint, account_security_state.last_login_fingerprint),
            last_login_ip = COALESCE(EXCLUDED.last_login_ip, account_security_state.last_login_ip),
            last_login_location = COALESCE(EXCLUDED.last_login_location, account_security_state.last_login_location),
            failed_login_count = EXCLUDED.failed_login_count,
            failed_login_window_started_at = EXCLUDED.failed_login_window_started_at,
            takeover_risk = EXCLUDED.takeover_risk,
            takeover_level = EXCLUDED.takeover_level,
            recommendation = EXCLUDED.recommendation,
            indicators = EXCLUDED.indicators,
            updated_at = CURRENT_TIMESTAMP
    """, (
        organization_id,
        user_id,
        password_at,
        sim_at,
        now if successful_login else None,
        device_data["fingerprint"] if successful_login else None,
        event.get("ip") if successful_login else None,
        event.get("location") if successful_login else None,
        failed_count,
        failed_window,
        takeover["score"],
        takeover["level"],
        takeover["recommendation"],
        Json(takeover["indicators"]),
    ))


def behavioral_context(cursor, organization_id: int, user_id: str, event_timestamp: str) -> dict:
    ensure_organization_tables(cursor)
    ensure_event_table(cursor)
    settings_data = behavior_settings(cursor, organization_id)
    cursor.execute("""
        SELECT trusted_event_count, amount_mean, known_devices, known_locations, hour_histogram
        FROM behavioral_profiles
        WHERE organization_id = %s AND user_id = %s
    """, (organization_id, user_id))
    profile = cursor.fetchone()

    if profile:
        trusted_event_count = profile[0] or 0
        average_amount = float(profile[1] or 0)
        known_devices = list(profile[2] or [])
        known_locations = list(profile[3] or [])
        hour_histogram = profile[4] or {}
    else:
        cursor.execute("""
            SELECT
                COUNT(*),
                COALESCE(AVG(amount), 0),
                COALESCE(ARRAY_AGG(DISTINCT LOWER(COALESCE(NULLIF(device_id, ''), NULLIF(device_type, ''))))
                    FILTER (WHERE COALESCE(NULLIF(device_id, ''), NULLIF(device_type, '')) IS NOT NULL), '{}'),
                COALESCE(ARRAY_AGG(DISTINCT LOWER(NULLIF(location, '')))
                    FILTER (WHERE location IS NOT NULL AND location <> ''), '{}')
            FROM events
            WHERE user_id = %s AND organization_id = %s
        """, (user_id, organization_id))
        history = cursor.fetchone()
        trusted_event_count = history[0] or 0
        average_amount = float(history[1] or 0)
        known_devices = list(history[2] or [])
        known_locations = list(history[3] or [])
        hour_histogram = {}
        if trusted_event_count:
            cursor.execute("""
                INSERT INTO behavioral_profiles (
                    organization_id, user_id, event_count, trusted_event_count,
                    amount_count, amount_mean, known_devices, known_locations,
                    hour_histogram, updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, '{}'::jsonb, CURRENT_TIMESTAMP)
                ON CONFLICT (organization_id, user_id) DO NOTHING
            """, (
                organization_id,
                user_id,
                trusted_event_count,
                trusted_event_count,
                trusted_event_count,
                average_amount,
                Json(known_devices),
                Json(known_locations),
            ))

    usual_start, usual_end = usual_hours(hour_histogram)
    timestamp = datetime.fromisoformat(event_timestamp.replace("Z", "+00:00")).replace(tzinfo=None)
    window_start = timestamp - timedelta(minutes=int(settings_data["velocity_window_minutes"]))
    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE LOWER(event_type) IN ('transaction', 'large_transfer', 'transfer', 'payment')),
            COUNT(*) FILTER (WHERE LOWER(event_type) IN ('login', 'login_success', 'login_failure', 'multiple_failed_logins'))
        FROM events
        WHERE user_id = %s
          AND organization_id = %s
          AND timestamp >= %s
          AND timestamp <= %s
    """, (user_id, organization_id, window_start, timestamp))
    velocity = cursor.fetchone()
    return {
        "trusted_event_count": trusted_event_count,
        "average_amount": average_amount,
        "known_devices": known_devices,
        "known_locations": known_locations,
        "usual_hour_start": usual_start,
        "usual_hour_end": usual_end,
        "transaction_velocity": velocity[0] or 0,
        "login_velocity": velocity[1] or 0,
        "settings": settings_data,
    }


def update_behavior_profile(
    cursor,
    organization_id: int,
    user_id: str,
    event: dict,
    trusted: bool,
    increment_event: bool = True,
):
    ensure_organization_tables(cursor)
    cursor.execute("""
        SELECT event_count, trusted_event_count, amount_count, amount_mean, amount_m2,
               known_devices, known_locations, hour_histogram, first_seen_at
        FROM behavioral_profiles
        WHERE organization_id = %s AND user_id = %s
    """, (organization_id, user_id))
    row = cursor.fetchone()
    now = datetime.fromisoformat(str(event["timestamp"]).replace("Z", "+00:00")).replace(tzinfo=None)
    event_count = (row[0] if row else 0) + (1 if increment_event else 0)
    trusted_count = (row[1] if row else 0) + (1 if trusted else 0)
    amount_count = row[2] if row else 0
    amount_mean = float(row[3] or 0) if row else 0
    amount_m2 = float(row[4] or 0) if row else 0
    known_devices = list(row[5] or []) if row else []
    known_locations = list(row[6] or []) if row else []
    hour_histogram = dict(row[7] or {}) if row else {}
    first_seen_at = row[8] if row else now

    if trusted:
        amount = float(event.get("amount") or 0)
        amount_count += 1
        delta = amount - amount_mean
        amount_mean += delta / amount_count
        amount_m2 += delta * (amount - amount_mean)
        device = str(event.get("device_id") or event.get("device_type") or event.get("device") or "").lower().strip()
        location = str(event.get("location") or "").lower().strip()
        if device and device not in known_devices:
            known_devices = (known_devices + [device])[-100:]
        if location and location not in known_locations:
            known_locations = (known_locations + [location])[-100:]
        hour = str(now.hour)
        hour_histogram[hour] = int(hour_histogram.get(hour, 0)) + 1

    cursor.execute("""
        INSERT INTO behavioral_profiles (
            organization_id, user_id, event_count, trusted_event_count, amount_count,
            amount_mean, amount_m2, known_devices, known_locations, hour_histogram,
            first_seen_at, last_seen_at, updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (organization_id, user_id) DO UPDATE SET
            event_count = EXCLUDED.event_count,
            trusted_event_count = EXCLUDED.trusted_event_count,
            amount_count = EXCLUDED.amount_count,
            amount_mean = EXCLUDED.amount_mean,
            amount_m2 = EXCLUDED.amount_m2,
            known_devices = EXCLUDED.known_devices,
            known_locations = EXCLUDED.known_locations,
            hour_histogram = EXCLUDED.hour_histogram,
            last_seen_at = EXCLUDED.last_seen_at,
            updated_at = CURRENT_TIMESTAMP
    """, (
        organization_id,
        user_id,
        event_count,
        trusted_count,
        amount_count,
        amount_mean,
        amount_m2,
        Json(known_devices),
        Json(known_locations),
        Json(hour_histogram),
        first_seen_at,
        now,
    ))


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


def invite_response(row) -> InviteResponse:
    invite_id, token, email, role, expires_at, used_at, created_by, created_at = row
    return InviteResponse(
        id=invite_id,
        token=token,
        invite_url=invite_url(token),
        email=email,
        role=role,
        expires_at=str(expires_at),
        used_at=str(used_at) if used_at else None,
        created_by=created_by,
        created_at=str(created_at),
    )


def organization_slug(name: str) -> str:
    base = "".join(character.lower() if character.isalnum() else "-" for character in name).strip("-")
    return "-".join(part for part in base.split("-") if part)[:80] or f"tenant-{secrets.token_hex(4)}"


@app.post("/organizations", response_model=OrganizationResponse)
def create_organization(
    payload: OrganizationCreateRequest,
    current_user: AuthUserResponse = Depends(get_current_user),
):
    require_admin(current_user)
    conn, cursor = get_db()
    ensure_auth_tables(cursor)
    cursor.execute("SELECT slug FROM organizations WHERE id = %s", (current_user.organization_id,))
    owner_organization = cursor.fetchone()
    if not owner_organization or owner_organization[0] != "boujuron":
        conn.close()
        raise HTTPException(status_code=403, detail="Only the Boujuron platform organization can provision tenants")
    slug = organization_slug(payload.name)
    cursor.execute("SELECT id FROM organizations WHERE slug = %s OR LOWER(name) = LOWER(%s)", (slug, payload.name.strip()))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=409, detail="Organization already exists")
    cursor.execute("""
        INSERT INTO organizations (name, slug)
        VALUES (%s, %s)
        RETURNING id, name, slug, created_at
    """, (payload.name.strip(), slug))
    organization = cursor.fetchone()
    cursor.execute("INSERT INTO organization_risk_settings (organization_id) VALUES (%s)", (organization[0],))
    token = create_invite_token()
    expires_at = datetime.utcnow() + timedelta(hours=24)
    cursor.execute("""
        INSERT INTO invite_tokens (token, email, role, expires_at, created_by, organization_id)
        VALUES (%s, %s, 'Admin', %s, %s, %s)
    """, (token, payload.admin_email.lower(), expires_at, current_user.id, organization[0]))
    conn.commit()
    conn.close()
    return OrganizationResponse(
        id=organization[0],
        name=organization[1],
        slug=organization[2],
        admin_invite_url=invite_url(token),
        created_at=str(organization[3]),
    )


@app.get("/organizations/current", response_model=OrganizationResponse)
def current_organization(current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    organization_id = current_user.organization_id or default_organization_id(cursor)
    cursor.execute("SELECT id, name, slug, created_at FROM organizations WHERE id = %s", (organization_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Organization not found")
    return OrganizationResponse(id=row[0], name=row[1], slug=row[2], created_at=str(row[3]))


@app.post("/auth/invites", response_model=InviteResponse)
def create_invite(payload: InviteCreateRequest, current_user: AuthUserResponse = Depends(get_current_user)):
    require_admin(current_user)
    role = payload.role if payload.role in ALLOWED_ROLES else "Read-Only Auditor"
    expires_in_hours = min(max(payload.expires_in_hours, 1), 24)
    conn, cursor = get_db()
    ensure_auth_tables(cursor)
    token = create_invite_token()
    expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)
    cursor.execute("""
        INSERT INTO invite_tokens (token, email, role, expires_at, created_by, organization_id)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, token, email, role, expires_at, used_at, %s AS created_by, created_at
    """, (
        token,
        payload.email.lower(),
        role,
        expires_at,
        current_user.id,
        current_user.organization_id or default_organization_id(cursor),
        current_user.name,
    ))
    row = cursor.fetchone()
    conn.commit()
    conn.close()
    return invite_response(row)


@app.get("/auth/invites", response_model=list[InviteResponse])
def list_invites(current_user: AuthUserResponse = Depends(get_current_user)):
    require_admin(current_user)
    conn, cursor = get_db()
    ensure_auth_tables(cursor)
    cursor.execute("""
        SELECT
            i.id,
            i.token,
            i.email,
            i.role,
            i.expires_at,
            i.used_at,
            u.name AS created_by,
            i.created_at
        FROM invite_tokens i
        LEFT JOIN app_users u ON u.id = i.created_by
        WHERE i.organization_id = %s
        ORDER BY i.created_at DESC
    """, (current_user.organization_id or default_organization_id(cursor),))
    rows = cursor.fetchall()
    conn.close()
    return [invite_response(row) for row in rows]


@app.post("/api-keys", response_model=ApiKeyResponse)
def create_api_key(payload: ApiKeyCreateRequest, current_user: AuthUserResponse = Depends(get_current_user)):
    require_admin(current_user)
    raw_key = f"bj_live_{secrets.token_urlsafe(32)}"
    prefix = raw_key[:16]
    conn, cursor = get_db()
    ensure_auth_tables(cursor)
    cursor.execute("""
        INSERT INTO client_api_keys (name, key_prefix, key_hash, created_by, organization_id)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, name, key_prefix, active, request_count, last_used_at, created_at
    """, (
        payload.name.strip(),
        prefix,
        hash_api_key(raw_key),
        current_user.id,
        current_user.organization_id or default_organization_id(cursor),
    ))
    row = cursor.fetchone()
    conn.commit()
    conn.close()
    return api_key_response(row, api_key=raw_key)


@app.get("/api-keys", response_model=list[ApiKeyResponse])
def list_api_keys(current_user: AuthUserResponse = Depends(get_current_user)):
    require_admin(current_user)
    conn, cursor = get_db()
    ensure_auth_tables(cursor)
    cursor.execute("""
        SELECT id, name, key_prefix, active, request_count, last_used_at, created_at
        FROM client_api_keys
        WHERE organization_id = %s
        ORDER BY created_at DESC
        LIMIT 100
    """, (current_user.organization_id or default_organization_id(cursor),))
    rows = cursor.fetchall()
    conn.close()
    return [api_key_response(row) for row in rows]


@app.delete("/api-keys/{key_id}")
def revoke_api_key(key_id: int, current_user: AuthUserResponse = Depends(get_current_user)):
    require_admin(current_user)
    conn, cursor = get_db()
    ensure_auth_tables(cursor)
    cursor.execute(
        "UPDATE client_api_keys SET active = FALSE WHERE id = %s AND organization_id = %s RETURNING id",
        (key_id, current_user.organization_id or default_organization_id(cursor)),
    )
    revoked = cursor.fetchone()
    conn.commit()
    conn.close()
    if not revoked:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"message": "API key revoked"}


@app.post("/api-keys/{key_id}/rotate", response_model=ApiKeyResponse)
def rotate_api_key(key_id: int, current_user: AuthUserResponse = Depends(get_current_user)):
    require_admin(current_user)
    conn, cursor = get_db()
    ensure_auth_tables(cursor)
    organization_id = current_user.organization_id or default_organization_id(cursor)
    cursor.execute("SELECT name FROM client_api_keys WHERE id = %s AND organization_id = %s AND active = TRUE", (key_id, organization_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Active API key not found")
    raw_key = f"bj_live_{secrets.token_urlsafe(32)}"
    cursor.execute("UPDATE client_api_keys SET active = FALSE WHERE id = %s", (key_id,))
    cursor.execute("""
        INSERT INTO client_api_keys (name, key_prefix, key_hash, created_by, organization_id, rotated_from)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, name, key_prefix, active, request_count, last_used_at, created_at
    """, (row[0], raw_key[:16], hash_api_key(raw_key), current_user.id, organization_id, key_id))
    created = cursor.fetchone()
    conn.commit()
    conn.close()
    return api_key_response(created, raw_key)


@app.get("/portal/usage", response_model=ApiKeyUsageResponse)
def portal_usage(current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    ensure_decision_rule_tables(cursor)
    organization_id = current_user.organization_id or default_organization_id(cursor)
    cursor.execute("""
        SELECT COUNT(*),
               COUNT(*) FILTER (WHERE created_at >= DATE_TRUNC('month', CURRENT_TIMESTAMP)),
               COUNT(*) FILTER (WHERE final_action = 'BLOCK'),
               COUNT(*) FILTER (WHERE final_action = 'CHALLENGE'),
               COUNT(*) FILTER (WHERE final_action = 'ALLOW')
        FROM action_decisions WHERE organization_id = %s
    """, (organization_id,))
    row = cursor.fetchone()
    conn.close()
    return ApiKeyUsageResponse(total_requests=row[0], requests_this_month=row[1], blocked=row[2], challenged=row[3], allowed=row[4])


@app.get("/portal/invoices", response_model=list[InvoiceResponse])
def portal_invoices(current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    ensure_auth_tables(cursor)
    organization_id = current_user.organization_id or default_organization_id(cursor)
    period = datetime.utcnow().strftime("%Y-%m")
    cursor.execute("""
        INSERT INTO invoices (organization_id, invoice_number, period, amount, currency, status)
        VALUES (%s, %s, %s, 0, 'USD', 'DRAFT')
        ON CONFLICT (invoice_number) DO NOTHING
    """, (organization_id, f"INV-{organization_id}-{period}", period))
    cursor.execute("""
        SELECT id, invoice_number, period, amount, currency, status, created_at
        FROM invoices WHERE organization_id = %s ORDER BY period DESC
    """, (organization_id,))
    rows = cursor.fetchall()
    conn.commit()
    conn.close()
    return [InvoiceResponse(id=r[0], invoice_number=r[1], period=r[2], amount=float(r[3]), currency=r[4], status=r[5], created_at=str(r[6])) for r in rows]


def behavior_settings_response(cursor, organization_id: int) -> BehaviorSettingsResponse:
    settings_data = behavior_settings(cursor, organization_id)
    cursor.execute("SELECT name FROM organizations WHERE id = %s", (organization_id,))
    organization = cursor.fetchone()
    return BehaviorSettingsResponse(
        organization_id=organization_id,
        organization_name=organization[0] if organization else "Organization",
        **settings_data,
    )


def rule_response(row) -> DecisionRuleResponse:
    return DecisionRuleResponse(
        id=row[0],
        organization_id=row[1],
        name=row[2],
        conditions=row[3] or [],
        action=row[4],
        score_adjustment=int(row[5] or 0),
        priority=int(row[6] or 100),
        enabled=bool(row[7]),
        created_by=row[8],
        created_at=str(row[9]),
        updated_at=str(row[10]),
    )


def compare_rule_value(actual, operator: str, expected) -> bool:
    if operator in {"GT", "GTE", "LT", "LTE"}:
        try:
            actual, expected = float(actual), float(expected)
        except (TypeError, ValueError):
            return False
    if operator == "EQ":
        return str(actual).lower() == str(expected).lower()
    if operator == "NEQ":
        return str(actual).lower() != str(expected).lower()
    if operator == "GT":
        return actual > expected
    if operator == "GTE":
        return actual >= expected
    if operator == "LT":
        return actual < expected
    if operator == "LTE":
        return actual <= expected
    if operator == "IN":
        values = expected if isinstance(expected, list) else [expected]
        return str(actual).lower() in {str(item).lower() for item in values}
    if operator == "CONTAINS":
        return str(expected).lower() in str(actual).lower()
    return False


def evaluate_decision_rules(cursor, organization_id: int, event: dict, result: dict, device_data: dict) -> dict:
    ensure_decision_rule_tables(cursor)
    cursor.execute("""
        SELECT id, name, conditions, action, score_adjustment
        FROM decision_rules
        WHERE organization_id = %s AND enabled = TRUE
        ORDER BY priority ASC, id ASC
    """, (organization_id,))
    context = {
        **event,
        "risk_score": result["risk_score"],
        "risk_level": result["risk_level"],
        "is_new_device": device_data["is_new_device"],
    }
    matched = []
    for rule_id, name, conditions, action, score_adjustment in cursor.fetchall():
        if all(compare_rule_value(context.get(item["field"]), item["operator"], item.get("value")) for item in (conditions or [])):
            matched.append({
                "id": rule_id,
                "name": name,
                "action": action,
                "score_adjustment": int(score_adjustment or 0),
            })
    strength = {"ALLOW": 0, "CHALLENGE": 1, "BLOCK": 2}
    model_action = {
        "ALLOW": "ALLOW",
        "VERIFY": "CHALLENGE",
        "BLOCK": "BLOCK",
        "LOCK_ACCOUNT": "BLOCK",
    }.get(result["action"], "CHALLENGE")
    final_action = model_action
    for rule in matched:
        if strength[rule["action"]] > strength[final_action]:
            final_action = rule["action"]
    if matched:
        adjustment = max(rule["score_adjustment"] for rule in matched)
        result["risk_score"] = min(100, result["risk_score"] + adjustment)
        result["risk_level"] = (
            "CRITICAL" if result["risk_score"] >= 90 else
            "HIGH" if result["risk_score"] >= 70 else
            "MEDIUM" if result["risk_score"] >= 40 else
            "LOW"
        )
        result["signals"].extend({
            "category": "RULE",
            "label": f"Policy matched: {rule['name']}",
            "points": rule["score_adjustment"],
            "evidence": f"Organization rule selected {rule['action']}",
        } for rule in matched)
        result["reasons"].extend(f"Policy matched: {rule['name']}" for rule in matched)
        result["reason"] = ", ".join(result["reasons"])
    if final_action == "BLOCK":
        result["risk_score"] = max(result["risk_score"], 70)
    elif final_action == "CHALLENGE":
        result["risk_score"] = max(result["risk_score"], 40)
    result["risk_level"] = (
        "CRITICAL" if result["risk_score"] >= 90 else
        "HIGH" if result["risk_score"] >= 70 else
        "MEDIUM" if result["risk_score"] >= 40 else
        "LOW"
    )
    result["action"] = final_action
    result["recommendation"] = {
        "ALLOW": "ALLOW",
        "CHALLENGE": "STEP_UP_VERIFICATION",
        "BLOCK": "AUTO_PND_FREEZE_ACCOUNT_AND_ESCALATE" if result["risk_level"] == "CRITICAL" else "AUTO_PND_BLOCK_TRANSACTION",
    }[final_action]
    result["confidence"] = min(99, max(float(result.get("confidence") or 55), result["risk_score"] + 4))
    return {
        "model_action": model_action,
        "final_action": final_action,
        "matched_rules": [rule["name"] for rule in matched],
    }


def reputation_hash(entity_type: str, value: str) -> str:
    normalized = str(value or "").strip().lower()
    return hmac.new(AUTH_SECRET.encode(), f"{entity_type}:{normalized}".encode(), hashlib.sha256).hexdigest()


def consortium_signal(cursor, organization_id: int, event: dict, device_data: dict) -> dict | None:
    ensure_decision_rule_tables(cursor)
    cursor.execute("SELECT enabled FROM consortium_settings WHERE organization_id = %s", (organization_id,))
    settings_row = cursor.fetchone()
    if not settings_row or not settings_row[0]:
        return None
    entities = [("DEVICE", device_data["fingerprint"]), ("IP", event.get("ip"))]
    total = 0
    organizations = set()
    for entity_type, value in entities:
        if not value:
            continue
        cursor.execute("""
            SELECT organization_id, confirmed_fraud_count, false_positive_count
            FROM consortium_reputation
            WHERE entity_type = %s AND entity_hash = %s AND organization_id <> %s
        """, (entity_type, reputation_hash(entity_type, value), organization_id))
        for other_org, fraud_count, false_count in cursor.fetchall():
            total += max(int(fraud_count or 0) - int(false_count or 0), 0)
            organizations.add(other_org)
    if not total:
        return None
    return {
        "category": "CONSORTIUM",
        "label": "Shared fraud-network reputation",
        "points": min(40, 10 + total * 5),
        "evidence": f"Hashed identity matched confirmed fraud at {len(organizations)} other organization(s)",
    }


def deliver_alerts(cursor, organization_id: int, alert: dict):
    severity = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    cursor.execute("""
        SELECT id, channel, target, minimum_risk
        FROM alert_destinations
        WHERE organization_id = %s AND enabled = TRUE
    """, (organization_id,))
    message = {
        "title": "HIGH RISK TRANSACTION",
        "user": alert["user_id"],
        "risk": alert["risk_score"],
        "action": alert["recommended_action"],
        "reason": alert["reason"],
    }
    for destination_id, channel, target, minimum_risk in cursor.fetchall():
        if severity.get(alert["risk_level"], 0) < severity.get(minimum_risk, 2):
            continue
        status = "SENT"
        try:
            if channel in {"SLACK", "TEAMS", "WEBHOOK"}:
                body = json.dumps({"text": f"{message['title']}\nUser: {message['user']}\nRisk: {message['risk']}\nAction: {message['action']}", **message}).encode()
                request = urllib.request.Request(target, data=body, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(request, timeout=4):
                    pass
            elif channel == "EMAIL":
                smtp_host = os.getenv("SMTP_HOST")
                if not smtp_host:
                    raise ValueError("SMTP_HOST is not configured")
                with smtplib.SMTP(smtp_host, int(os.getenv("SMTP_PORT", "587")), timeout=5) as smtp:
                    smtp.starttls()
                    smtp.login(os.getenv("SMTP_USERNAME", ""), os.getenv("SMTP_PASSWORD", ""))
                    smtp.sendmail(os.getenv("SMTP_FROM", "alerts@boujuron.ai"), target, f"Subject: Boujuron Fraud Alert\n\n{json.dumps(message, indent=2)}")
        except Exception as exc:
            status = f"FAILED: {str(exc)[:120]}"
        cursor.execute("UPDATE alert_destinations SET last_status = %s, last_sent_at = CURRENT_TIMESTAMP WHERE id = %s", (status, destination_id))


@app.get("/decision-rules", response_model=list[DecisionRuleResponse])
def list_decision_rules(current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    ensure_decision_rule_tables(cursor)
    organization_id = current_user.organization_id or default_organization_id(cursor)
    cursor.execute("""
        SELECT r.id, r.organization_id, r.name, r.conditions, r.action, r.score_adjustment,
               r.priority, r.enabled, u.name, r.created_at, r.updated_at
        FROM decision_rules r
        LEFT JOIN app_users u ON u.id = r.created_by
        WHERE r.organization_id = %s
        ORDER BY r.priority, r.id
    """, (organization_id,))
    rows = cursor.fetchall()
    conn.close()
    return [rule_response(row) for row in rows]


@app.post("/decision-rules", response_model=DecisionRuleResponse)
def create_decision_rule(
    payload: DecisionRuleRequest,
    current_user: AuthUserResponse = Depends(get_current_user),
):
    require_admin(current_user)
    conn, cursor = get_db()
    ensure_auth_tables(cursor)
    ensure_decision_rule_tables(cursor)
    organization_id = current_user.organization_id or default_organization_id(cursor)
    try:
        cursor.execute("""
            INSERT INTO decision_rules (
                organization_id, name, conditions, action, score_adjustment,
                priority, enabled, created_by
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, organization_id, name, conditions, action, score_adjustment,
                      priority, enabled, %s, created_at, updated_at
        """, (
            organization_id,
            payload.name.strip(),
            Json([condition.model_dump() for condition in payload.conditions]),
            payload.action,
            payload.score_adjustment,
            payload.priority,
            payload.enabled,
            current_user.id,
            current_user.name,
        ))
    except psycopg2.errors.UniqueViolation as exc:
        conn.rollback()
        conn.close()
        raise HTTPException(status_code=409, detail="A rule with this name already exists") from exc
    row = cursor.fetchone()
    conn.commit()
    conn.close()
    return rule_response(row)


@app.patch("/decision-rules/{rule_id}", response_model=DecisionRuleResponse)
def update_decision_rule(
    rule_id: int,
    payload: DecisionRuleRequest,
    current_user: AuthUserResponse = Depends(get_current_user),
):
    require_admin(current_user)
    conn, cursor = get_db()
    ensure_decision_rule_tables(cursor)
    organization_id = current_user.organization_id or default_organization_id(cursor)
    cursor.execute("""
        UPDATE decision_rules
        SET name = %s, conditions = %s, action = %s, score_adjustment = %s,
            priority = %s, enabled = %s, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s AND organization_id = %s
        RETURNING id, organization_id, name, conditions, action, score_adjustment,
                  priority, enabled, %s, created_at, updated_at
    """, (
        payload.name.strip(),
        Json([condition.model_dump() for condition in payload.conditions]),
        payload.action,
        payload.score_adjustment,
        payload.priority,
        payload.enabled,
        rule_id,
        organization_id,
        current_user.name,
    ))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Rule not found")
    conn.commit()
    conn.close()
    return rule_response(row)


@app.delete("/decision-rules/{rule_id}")
def delete_decision_rule(rule_id: int, current_user: AuthUserResponse = Depends(get_current_user)):
    require_admin(current_user)
    conn, cursor = get_db()
    organization_id = current_user.organization_id or default_organization_id(cursor)
    cursor.execute(
        "DELETE FROM decision_rules WHERE id = %s AND organization_id = %s RETURNING id",
        (rule_id, organization_id),
    )
    deleted = cursor.fetchone()
    conn.commit()
    conn.close()
    if not deleted:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"message": "Rule deleted"}


@app.get("/alert-destinations", response_model=list[AlertDestinationResponse])
def list_alert_destinations(current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    ensure_decision_rule_tables(cursor)
    organization_id = current_user.organization_id or default_organization_id(cursor)
    cursor.execute("""
        SELECT id, name, channel, target, minimum_risk, enabled, last_status, last_sent_at, created_at
        FROM alert_destinations WHERE organization_id = %s ORDER BY id
    """, (organization_id,))
    rows = cursor.fetchall()
    conn.close()
    return [AlertDestinationResponse(id=r[0], name=r[1], channel=r[2], target=r[3], minimum_risk=r[4], enabled=r[5], last_status=r[6], last_sent_at=str(r[7]) if r[7] else None, created_at=str(r[8])) for r in rows]


@app.post("/alert-destinations", response_model=AlertDestinationResponse)
def create_alert_destination(payload: AlertDestinationRequest, current_user: AuthUserResponse = Depends(get_current_user)):
    require_admin(current_user)
    conn, cursor = get_db()
    ensure_decision_rule_tables(cursor)
    organization_id = current_user.organization_id or default_organization_id(cursor)
    cursor.execute("""
        INSERT INTO alert_destinations (organization_id, name, channel, target, minimum_risk, enabled)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id, name, channel, target, minimum_risk, enabled, last_status, last_sent_at, created_at
    """, (organization_id, payload.name, payload.channel, payload.target, payload.minimum_risk.upper(), payload.enabled))
    r = cursor.fetchone()
    conn.commit()
    conn.close()
    return AlertDestinationResponse(id=r[0], name=r[1], channel=r[2], target=r[3], minimum_risk=r[4], enabled=r[5], last_status=r[6], last_sent_at=None, created_at=str(r[8]))


@app.delete("/alert-destinations/{destination_id}")
def delete_alert_destination(destination_id: int, current_user: AuthUserResponse = Depends(get_current_user)):
    require_admin(current_user)
    conn, cursor = get_db()
    organization_id = current_user.organization_id or default_organization_id(cursor)
    cursor.execute("DELETE FROM alert_destinations WHERE id = %s AND organization_id = %s RETURNING id", (destination_id, organization_id))
    deleted = cursor.fetchone()
    conn.commit()
    conn.close()
    if not deleted:
        raise HTTPException(status_code=404, detail="Destination not found")
    return {"message": "Destination deleted"}


@app.get("/consortium/settings", response_model=ConsortiumSettingsResponse)
def get_consortium_settings(current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    ensure_decision_rule_tables(cursor)
    organization_id = current_user.organization_id or default_organization_id(cursor)
    cursor.execute("""
        INSERT INTO consortium_settings (organization_id) VALUES (%s)
        ON CONFLICT (organization_id) DO NOTHING
    """, (organization_id,))
    cursor.execute("SELECT enabled, share_devices, share_ips, share_emails, share_phones FROM consortium_settings WHERE organization_id = %s", (organization_id,))
    row = cursor.fetchone()
    conn.commit()
    conn.close()
    return ConsortiumSettingsResponse(enabled=row[0], share_devices=row[1], share_ips=row[2], share_emails=row[3], share_phones=row[4])


@app.patch("/consortium/settings", response_model=ConsortiumSettingsResponse)
def update_consortium_settings(payload: ConsortiumSettingsUpdate, current_user: AuthUserResponse = Depends(get_current_user)):
    require_admin(current_user)
    conn, cursor = get_db()
    ensure_decision_rule_tables(cursor)
    organization_id = current_user.organization_id or default_organization_id(cursor)
    cursor.execute("""
        INSERT INTO consortium_settings (organization_id, enabled, share_devices, share_ips, share_emails, share_phones)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (organization_id) DO UPDATE SET enabled=EXCLUDED.enabled,
          share_devices=EXCLUDED.share_devices, share_ips=EXCLUDED.share_ips,
          share_emails=EXCLUDED.share_emails, share_phones=EXCLUDED.share_phones,
          updated_at=CURRENT_TIMESTAMP
        RETURNING enabled, share_devices, share_ips, share_emails, share_phones
    """, (organization_id, payload.enabled, payload.share_devices, payload.share_ips, payload.share_emails, payload.share_phones))
    row = cursor.fetchone()
    conn.commit()
    conn.close()
    return ConsortiumSettingsResponse(enabled=row[0], share_devices=row[1], share_ips=row[2], share_emails=row[3], share_phones=row[4])


@app.get("/behavior/settings", response_model=BehaviorSettingsResponse)
def get_behavior_settings(current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    organization_id = current_user.organization_id or default_organization_id(cursor)
    response = behavior_settings_response(cursor, organization_id)
    conn.commit()
    conn.close()
    return response


@app.patch("/behavior/settings", response_model=BehaviorSettingsResponse)
def update_behavior_settings(
    payload: BehaviorSettingsUpdate,
    current_user: AuthUserResponse = Depends(get_current_user),
):
    require_admin(current_user)
    changes = payload.model_dump(exclude_unset=True)
    conn, cursor = get_db()
    organization_id = current_user.organization_id or default_organization_id(cursor)
    behavior_settings(cursor, organization_id)
    if changes:
        clauses = [f"{field} = %s" for field in changes]
        values = list(changes.values()) + [organization_id]
        cursor.execute(f"""
            UPDATE organization_risk_settings
            SET {', '.join(clauses)}, updated_at = CURRENT_TIMESTAMP
            WHERE organization_id = %s
        """, values)
    response = behavior_settings_response(cursor, organization_id)
    conn.commit()
    conn.close()
    return response


@app.get("/behavior/evaluation", response_model=BehaviorEvaluationResponse)
def behavior_evaluation(current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    ensure_risk_decision_table(cursor)
    ensure_organization_tables(cursor)
    organization_id = current_user.organization_id or default_organization_id(cursor)
    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE analyst_feedback IS NOT NULL),
            COUNT(*) FILTER (WHERE analyst_feedback = 'TRUE_FRAUD'),
            COUNT(*) FILTER (WHERE analyst_feedback = 'FALSE_POSITIVE'),
            COUNT(*) FILTER (WHERE analyst_feedback = 'NEEDS_REVIEW')
        FROM risk_decisions
        WHERE organization_id = %s
    """, (organization_id,))
    labeled, confirmed, false_positive, needs_review = cursor.fetchone()
    cursor.execute("""
        SELECT COUNT(*), COALESCE(SUM(trusted_event_count), 0)
        FROM behavioral_profiles
        WHERE organization_id = %s AND trusted_event_count > 0
    """, (organization_id,))
    profiles_learning, trusted_events = cursor.fetchone()
    conn.close()
    denominator = confirmed + false_positive
    precision = round((confirmed / denominator) * 100, 1) if denominator else 0
    false_positive_rate = round((false_positive / denominator) * 100, 1) if denominator else 0
    return BehaviorEvaluationResponse(
        labeled_decisions=labeled,
        confirmed_fraud=confirmed,
        false_positives=false_positive,
        needs_review=needs_review,
        precision=precision,
        false_positive_rate=false_positive_rate,
        profiles_learning=profiles_learning,
        trusted_events_learned=trusted_events,
    )


@app.post("/auth/register", response_model=AuthTokenResponse)
def register(payload: AuthRegisterRequest):
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    conn, cursor = get_db()
    ensure_auth_tables(cursor)
    invite_token = payload.invite_token.strip().upper()
    cursor.execute("""
        SELECT id, email, role, expires_at, used_at, organization_id
        FROM invite_tokens
        WHERE token = %s
    """, (invite_token,))
    invite = cursor.fetchone()
    if not invite:
        conn.close()
        raise HTTPException(status_code=403, detail="A valid invite token is required")

    invite_id, invite_email, invite_role, expires_at, used_at, organization_id = invite
    if used_at is not None:
        conn.close()
        raise HTTPException(status_code=403, detail="Invite token has already been used")
    if expires_at < datetime.utcnow():
        conn.close()
        raise HTTPException(status_code=403, detail="Invite token has expired")
    if invite_email.lower() != payload.email.lower():
        conn.close()
        raise HTTPException(status_code=403, detail="Invite token is not valid for this email")

    role = invite_role if invite_role in ALLOWED_ROLES else "Read-Only Auditor"
    cursor.execute("SELECT id FROM app_users WHERE email = %s", (payload.email.lower(),))
    if cursor.fetchone():
        conn.close()
        raise HTTPException(status_code=409, detail="Email is already registered")

    cursor.execute("""
        INSERT INTO app_users (name, email, password_hash, role, organization_id)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, name, email, role, organization_id
    """, (payload.name.strip(), payload.email.lower(), hash_password(payload.password), role, organization_id))
    row = cursor.fetchone()
    cursor.execute("""
        UPDATE invite_tokens
        SET used_at = CURRENT_TIMESTAMP, used_by = %s
        WHERE id = %s
    """, (row[0], invite_id))
    conn.commit()
    conn.close()
    user = AuthUserResponse(id=row[0], name=row[1], email=row[2], role=row[3], organization_id=row[4])
    return AuthTokenResponse(access_token=create_token(user), user=user)


@app.post("/auth/login", response_model=AuthTokenResponse)
def login(payload: AuthLoginRequest):
    conn, cursor = get_db()
    ensure_auth_tables(cursor)
    cursor.execute("SELECT id, name, email, role, password_hash, organization_id FROM app_users WHERE email = %s", (payload.email.lower(),))
    row = cursor.fetchone()
    conn.close()
    if not row or not verify_password(payload.password, row[4]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user = AuthUserResponse(id=row[0], name=row[1], email=row[2], role=row[3], organization_id=row[5])
    return AuthTokenResponse(access_token=create_token(user), user=user)


@app.post("/auth/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(payload: ForgotPasswordRequest):
    conn, cursor = get_db()
    ensure_auth_tables(cursor)
    cursor.execute("SELECT id FROM app_users WHERE email = %s", (payload.email.lower(),))
    row = cursor.fetchone()

    if not row:
        conn.close()
        return ForgotPasswordResponse(message="If the email exists, a reset link has been generated.")

    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=PASSWORD_RESET_TTL_MINUTES)
    cursor.execute("""
        INSERT INTO password_reset_tokens (user_id, token, expires_at)
        VALUES (%s, %s, %s)
    """, (row[0], token, expires_at))
    conn.commit()
    conn.close()

    reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={token}"
    return ForgotPasswordResponse(
        message="Password reset link generated.",
        reset_token=token if settings.ENVIRONMENT != "production" else None,
        reset_url=reset_url if settings.ENVIRONMENT != "production" else None,
    )


@app.post("/auth/reset-password")
def reset_password(payload: ResetPasswordRequest):
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    conn, cursor = get_db()
    ensure_auth_tables(cursor)
    cursor.execute("""
        SELECT id, user_id, expires_at, used_at
        FROM password_reset_tokens
        WHERE token = %s
    """, (payload.token,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=400, detail="Invalid reset token")

    token_id, user_id, expires_at, used_at = row
    if used_at is not None or expires_at < datetime.utcnow():
        conn.close()
        raise HTTPException(status_code=400, detail="Reset token has expired")

    cursor.execute("UPDATE app_users SET password_hash = %s WHERE id = %s", (hash_password(payload.password), user_id))
    cursor.execute("UPDATE password_reset_tokens SET used_at = CURRENT_TIMESTAMP WHERE id = %s", (token_id,))
    conn.commit()
    conn.close()
    return {"message": "Password reset successfully"}


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


@app.get("/health")
def health():
    return {"status": "ok", "service": "boujuron-dashboard-api"}


@app.get("/favicon.svg")
def serve_favicon():
    favicon_path = FRONTEND_DIST / "favicon.svg"
    if favicon_path.exists():
        return FileResponse(favicon_path, media_type="image/svg+xml")
    return Response(status_code=404)


def risk_response_from_row(row) -> RiskScoreResponse:
    return RiskScoreResponse(
        decision_id=row[0],
        transaction_id=row[1],
        transaction_direction=row[2] or "DEBIT",
        user_id=row[3],
        risk_score=row[4],
        risk_level=row[5],
        action=row[6],
        recommendation=row[7] or row[6],
        confidence=float(row[8] or 0),
        reasons=row[9] or [],
        signals=row[10] or [],
        behavioral_match=bool(row[11]),
        device_intelligence=row[12],
        account_takeover=row[13],
        action_decision_id=row[14],
        matched_rules=row[15] or [],
        created_at=str(row[16]),
    )


@app.post("/risk-score", response_model=RiskScoreResponse)
async def score_risk(
    payload: RiskScoreRequest,
    client=Depends(authenticate_risk_client),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if idempotency_key and len(idempotency_key) > 160:
        raise HTTPException(status_code=400, detail="Idempotency-Key must be 160 characters or fewer")

    event = payload.model_dump()
    event["device_type"] = payload.device_type or payload.device or ""
    event["timestamp"] = payload.timestamp or datetime.utcnow().isoformat()
    event["transaction_direction"] = payload.transaction_direction
    transaction_id = payload.transaction_id or f"txn_{secrets.token_hex(10)}"
    source = f"{client['type']}:{client['name']}"

    conn, cursor = get_db()
    prepare_analytics_tables(cursor)
    organization_id = client.get("organization_id") or default_organization_id(cursor)

    if idempotency_key:
        cursor.execute("""
            SELECT id, transaction_id, transaction_direction, user_id, risk_score, risk_level, action, recommendation, confidence,
                   reasons, signals, behavioral_match, device_intelligence, account_takeover,
                   action_decision_id, matched_rules, created_at
            FROM risk_decisions
            WHERE idempotency_key = %s AND organization_id = %s
        """, (idempotency_key, organization_id))
        existing = cursor.fetchone()
        if existing:
            conn.close()
            return risk_response_from_row(existing)

    device_data = load_device_intelligence(cursor, organization_id, payload.user_id, event)
    takeover_context = load_account_takeover_context(
        cursor,
        organization_id,
        payload.user_id,
        event,
        device_data,
    )
    behavior = behavioral_context(cursor, organization_id, payload.user_id, event["timestamp"])
    behavior["device_intelligence"] = device_data
    behavior["account_takeover"] = takeover_context
    result = analyze_event(event, behavior)
    shared_signal = consortium_signal(cursor, organization_id, event, device_data)
    if shared_signal:
        result["signals"].append(shared_signal)
        result["reasons"].append(shared_signal["label"])
        result["reason"] = ", ".join(result["reasons"])
        result["risk_score"] = min(100, result["risk_score"] + shared_signal["points"])
        result["risk_level"] = "CRITICAL" if result["risk_score"] >= 90 else "HIGH" if result["risk_score"] >= 70 else "MEDIUM"
        result["recommendation"] = recommended_action_from_risk(result["risk_level"])
        result["action"] = result["recommendation"]
    action_evaluation = evaluate_decision_rules(cursor, organization_id, event, result, device_data)
    persist_device_intelligence(cursor, organization_id, payload.user_id, event, device_data, result)
    persist_account_security_state(
        cursor,
        organization_id,
        payload.user_id,
        event,
        device_data,
        result["account_takeover"],
        takeover_context,
    )
    settings_data = behavior["settings"]
    trusted_for_learning = bool(
        settings_data["adaptive_learning_enabled"]
        and result["risk_score"] <= int(settings_data["trusted_learning_max_score"])
    )
    metadata = {
        **payload.metadata,
        "is_rooted": payload.is_rooted,
        "is_emulator": payload.is_emulator,
        "browser_tampering": payload.browser_tampering,
        "sim_swap_detected": payload.sim_swap_detected,
        "password_changed_recently": payload.password_changed_recently,
        "new_beneficiary_added": payload.new_beneficiary_added,
        "mule_account_suspected": payload.mule_account_suspected,
        "failed_login_count": payload.failed_login_count,
        "accounts_from_ip": payload.accounts_from_ip,
        "accounts_from_device": payload.accounts_from_device,
        "registration_count": payload.registration_count,
        "automation_score": payload.automation_score,
        "repeated_failed_payments": payload.repeated_failed_payments,
        "rapid_credit_count": payload.rapid_credit_count,
        "different_sender_count": payload.different_sender_count,
        "debits_after_credit_count": payload.debits_after_credit_count,
        "dormant_days": payload.dormant_days,
        "credit_frequency_count": payload.credit_frequency_count,
        "suspicious_sender": payload.suspicious_sender,
        "chargeback_risk": payload.chargeback_risk,
        "channel": payload.channel,
    }

    cursor.execute("""
        INSERT INTO events (
            organization_id, transaction_id, transaction_direction, user_id, amount, location, event_type, device_type,
            device_id, network, ip, timestamp, metadata, source
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        organization_id,
        transaction_id,
        payload.transaction_direction,
        payload.user_id,
        payload.amount,
        payload.location,
        payload.event_type,
        event["device_type"],
        payload.device_id,
        payload.network,
        payload.ip,
        event["timestamp"],
        Json(metadata),
        source,
    ))

    cursor.execute("""
        INSERT INTO risk_decisions (
            organization_id, transaction_id, transaction_direction, idempotency_key, user_id, risk_score, risk_level,
            action, recommendation, confidence, reasons, signals, behavioral_match,
            request_payload, source, learned, device_intelligence, account_takeover
            , matched_rules
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, transaction_id, transaction_direction, user_id, risk_score, risk_level, action,
                  recommendation, confidence, reasons, signals, behavioral_match,
                  device_intelligence, account_takeover, action_decision_id, matched_rules, created_at
    """, (
        organization_id,
        transaction_id,
        payload.transaction_direction,
        idempotency_key,
        payload.user_id,
        result["risk_score"],
        result["risk_level"],
        result["action"],
        result["recommendation"],
        result["confidence"],
        Json(result["reasons"]),
        Json(result["signals"]),
        result["behavioral_match"],
        Json(event),
        source,
        trusted_for_learning,
        Json(device_data),
        Json(result["account_takeover"]),
        Json(action_evaluation["matched_rules"]),
    ))
    decision_row = cursor.fetchone()
    cursor.execute("""
        INSERT INTO action_decisions (
            organization_id, risk_decision_id, transaction_id, user_id,
            model_action, final_action, matched_rules, status, reason
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, 'DECIDED', %s)
        RETURNING id
    """, (
        organization_id,
        decision_row[0],
        transaction_id,
        payload.user_id,
        action_evaluation["model_action"],
        action_evaluation["final_action"],
        Json(action_evaluation["matched_rules"]),
        result["reason"],
    ))
    action_decision_id = cursor.fetchone()[0]
    cursor.execute(
        "UPDATE risk_decisions SET action_decision_id = %s WHERE id = %s",
        (action_decision_id, decision_row[0]),
    )
    decision_row = (*decision_row[:14], action_decision_id, decision_row[15], decision_row[16])

    audit_log(
        cursor,
        organization_id,
        None,
        transaction_id,
        payload.user_id,
        "RISK_DECISION_RECORDED",
        None,
        result["risk_level"],
        f"{result['recommendation']} decision recorded with score {result['risk_score']} and confidence {result['confidence']}%",
    )
    cursor.execute("""
        INSERT INTO fraud_alerts (
            organization_id, risk_decision_id, transaction_id, transaction_direction, user_id, reason, risk_score, risk_level, timestamp,
            recommended_action, confidence, signals_triggered, behavioral_match
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        organization_id,
        decision_row[0],
        transaction_id,
        payload.transaction_direction,
        payload.user_id,
        result["reason"],
        result["risk_score"],
        result["risk_level"],
        event["timestamp"],
        result["recommendation"],
        result["confidence"],
        len(result["signals"]),
        result["behavioral_match"],
    ))
    alert_id = cursor.fetchone()[0]
    materialize_cases_from_alerts(cursor, organization_id)
    alert = {
        "id": alert_id,
        "transaction_id": transaction_id,
        "transaction_direction": payload.transaction_direction,
        "user_id": payload.user_id,
        "reason": result["reason"],
        "risk_score": str(result["risk_score"]),
        "risk_level": result["risk_level"],
        "timestamp": event["timestamp"],
        "recommended_action": result["recommendation"],
        "confidence": float(result["confidence"]),
        "signals_triggered": len(result["signals"]),
        "behavioral_match": result["behavioral_match"],
    }
    deliver_alerts(cursor, organization_id, alert)

    update_behavior_profile(
        cursor,
        organization_id,
        payload.user_id,
        event,
        trusted=trusted_for_learning,
    )
    conn.commit()
    conn.close()

    if alert:
        await broadcast_alert(alert, organization_id)

    return risk_response_from_row(decision_row)


@app.websocket("/ws/fraud")
async def ws_fraud(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401)
        return
    try:
        payload = decode_token(token)
        conn, cursor = get_db()
        ensure_auth_tables(cursor)
        cursor.execute("SELECT organization_id FROM app_users WHERE id = %s", (payload["uid"],))
        row = cursor.fetchone()
        conn.close()
        if not row:
            raise ValueError("user missing")
        organization_id = row[0]
    except Exception:
        await websocket.close(code=4401)
        return
    await websocket.accept()
    connection = {"websocket": websocket, "organization_id": organization_id}
    clients.append(connection)

    try:
        while True:
            await asyncio.sleep(1)
    except Exception:
        if connection in clients:
            clients.remove(connection)

@app.post("/internal/fraud")
async def push_fraud(
    event: dict,
    x_internal_secret: str | None = Header(default=None, alias="X-Internal-Secret"),
):
    if not x_internal_secret or not hmac.compare_digest(x_internal_secret, AUTH_SECRET):
        raise HTTPException(status_code=401, detail="Invalid internal service secret")
    organization_id = event.pop("organization_id", None)
    if organization_id is None:
        conn, cursor = get_db()
        organization_id = default_organization_id(cursor)
        conn.commit()
        conn.close()
    await broadcast_alert(event, int(organization_id))
    return {"status": "sent"}


@app.post("/demo/fraud-event", response_model=FraudAlertResponse)
async def create_demo_fraud_event(
    payload: DemoFraudEventRequest,
    current_user: AuthUserResponse = Depends(get_current_user),
):
    event = payload.model_dump()
    event["timestamp"] = event.get("timestamp") or datetime.utcnow().isoformat()
    result = analyze_event(event)
    reason = result["reason"]
    risk_score = int(result["risk_score"])
    risk_level = result["risk_level"]
    recommended_action = recommended_action_from_risk(risk_level)
    signals_triggered = 0 if reason == "Normal activity" else len([item for item in reason.split(",") if item.strip()])
    behavioral_match = risk_score < 40
    confidence = float(result["confidence"])
    transaction_id = f"demo-{secrets.token_hex(4)}"

    conn, cursor = get_db()
    prepare_analytics_tables(cursor)
    organization_id = current_user.organization_id or default_organization_id(cursor)
    cursor.execute("""
        INSERT INTO events (organization_id, transaction_id, transaction_direction, user_id, amount, location, event_type, device_type, network, ip, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, (
        organization_id,
        transaction_id,
        payload.transaction_direction,
        payload.user_id,
        payload.amount,
        payload.location,
        payload.event_type,
        payload.device_type,
        payload.network,
        payload.ip,
        event["timestamp"],
    ))
    cursor.execute("""
        INSERT INTO fraud_alerts (
            organization_id,
            transaction_id,
            transaction_direction,
            user_id,
            reason,
            risk_score,
            risk_level,
            timestamp,
            recommended_action,
            confidence,
            signals_triggered,
            behavioral_match
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (
        organization_id,
        transaction_id,
        payload.transaction_direction,
        payload.user_id,
        reason,
        risk_score,
        risk_level,
        event["timestamp"],
        recommended_action,
        confidence,
        signals_triggered,
        behavioral_match,
    ))
    alert_id = cursor.fetchone()[0]
    materialize_cases_from_alerts(cursor, organization_id)
    conn.commit()
    conn.close()

    alert = FraudAlertResponse(
        transaction_id=transaction_id,
        transaction_direction=payload.transaction_direction,
        user_id=payload.user_id,
        reason=reason,
        timestamp=event["timestamp"],
        risk_score=str(risk_score),
        risk_level=risk_level,
        recommended_action=recommended_action,
        confidence=float(confidence),
        signals_triggered=signals_triggered,
        behavioral_match=behavioral_match,
    )
    socket_event = alert.model_dump()
    socket_event["id"] = alert_id
    socket_event["created_by"] = current_user.name
    await broadcast_alert(socket_event, organization_id)
    return alert


@app.get("/events", response_model=list[EventResponse])
def get_events(limit: int = Query(50), current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    organization_id = current_user.organization_id or default_organization_id(cursor)

    cursor.execute("""
        SELECT user_id, event_type, device_type, ip, timestamp
        FROM events
        WHERE organization_id = %s
        ORDER BY id DESC LIMIT %s
    """, (organization_id, limit))

    rows = cursor.fetchall()

    conn.close()

    return [EventResponse(*row) for row in rows]

@app.get("/fraud-alerts", response_model=list[FraudAlertResponse])
def get_fraud(limit: int = Query(50), current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()

    ensure_fraud_alert_columns(cursor)
    organization_id = current_user.organization_id or default_organization_id(cursor)
    materialize_cases_from_alerts(cursor, organization_id)
    conn.commit()

    cursor.execute("""
        SELECT
            f.id,
            c.id,
            c.case_number,
            c.status,
            c.analyst_feedback,
            latest_note.note,
            f.transaction_id,
            f.transaction_direction,
            f.user_id,
            f.reason,
            f.timestamp,
            f.risk_score,
            f.risk_level,
            f.recommended_action,
            f.confidence,
            f.signals_triggered,
            f.behavioral_match
        FROM fraud_alerts f
        LEFT JOIN cases c ON c.fraud_alert_id = f.id
        LEFT JOIN LATERAL (
            SELECT note
            FROM case_notes
            WHERE case_id = c.id
            ORDER BY id DESC
            LIMIT 1
        ) latest_note ON TRUE
        WHERE f.organization_id = %s
        ORDER BY f.id DESC LIMIT %s
    """, (organization_id, limit))

    rows = cursor.fetchall()

    conn.close()

    return [
        FraudAlertResponse(
            id=r[0],
            case_id=r[1],
            case_number=r[2],
            case_status=r[3],
            analyst_feedback=r[4],
            closure_note=r[5],
            transaction_id=r[6],
            transaction_direction=r[7],
            user_id=r[8],
            reason=r[9],
            timestamp=str(r[10]),
            risk_score=str(r[11]),
            risk_level=r[12],
            recommended_action=r[13],
            confidence=float(r[14]) if r[14] is not None else None,
            signals_triggered=r[15],
            behavioral_match=r[16]
        )
        for r in rows
    ]

@app.get("/users/{user_id}/activity")
def get_user_activity(user_id: str, current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    organization_id = current_user.organization_id or default_organization_id(cursor)

    cursor.execute("""
        SELECT user_id, event_type, device_type, ip, timestamp
        FROM events WHERE user_id = %s AND organization_id = %s
    """, (user_id, organization_id))

    events = cursor.fetchall()

    cursor.execute("""
        SELECT user_id, reason, timestamp
        FROM fraud_alerts WHERE user_id = %s AND organization_id = %s
    """, (user_id, organization_id))

    frauds = cursor.fetchall()

    conn.close()

    return {
        "events": events,
        "fraud_alerts": frauds
    }


@app.get("/customers/{user_id}/profile", response_model=UserProfileResponse)
def get_user_profile(user_id: str, current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    prepare_analytics_tables(cursor)
    organization_id = current_user.organization_id or default_organization_id(cursor)

    cursor.execute("""
        SELECT event_type, device_type, ip, location, network, amount, timestamp
        FROM events
        WHERE user_id = %s AND organization_id = %s
        ORDER BY timestamp DESC NULLS LAST, id DESC
        LIMIT 25
    """, (user_id, organization_id))
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
        WHERE user_id = %s AND organization_id = %s
        ORDER BY timestamp DESC NULLS LAST, id DESC
        LIMIT 20
    """, (user_id, organization_id))
    alert_rows = cursor.fetchall()

    cursor.execute("""
        SELECT fingerprint, label, status, trust_score, first_seen_at, last_seen_at,
               event_count, last_ip, last_location, integrity_flags
        FROM device_fingerprints
        WHERE organization_id = %s AND user_id = %s
        ORDER BY last_seen_at DESC
        LIMIT 20
    """, (organization_id, user_id))
    device_rows = cursor.fetchall()

    cursor.execute("""
        SELECT takeover_risk, takeover_level, recommendation, failed_login_count,
               password_changed_at, sim_changed_at, last_successful_login_at,
               last_login_location, last_login_ip, last_login_fingerprint, indicators
        FROM account_security_state
        WHERE organization_id = %s AND user_id = %s
    """, (organization_id, user_id))
    security_row = cursor.fetchone()
    conn.commit()
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
    device_inventory = [
        DeviceProfileResponse(
            fingerprint=row[0],
            label=row[1] or "Unknown device",
            status=row[2],
            trust_score=int(row[3] or 0),
            first_seen_at=str(row[4]),
            last_seen_at=str(row[5]),
            event_count=int(row[6] or 0),
            last_ip=row[7],
            last_location=row[8],
            integrity_flags=list(row[9] or []),
        )
        for row in device_rows
    ]
    account_security = None
    if security_row:
        account_security = AccountSecurityResponse(
            takeover_risk=int(security_row[0] or 0),
            takeover_level=security_row[1] or "LOW",
            recommendation=security_row[2] or "ALLOW",
            recent_failed_logins=int(security_row[3] or 0),
            password_changed_at=str(security_row[4]) if security_row[4] else None,
            sim_changed_at=str(security_row[5]) if security_row[5] else None,
            last_successful_login_at=str(security_row[6]) if security_row[6] else None,
            last_login_location=security_row[7],
            last_login_ip=security_row[8],
            last_login_device=security_row[9],
            indicators=list(security_row[10] or []),
        )

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
        device_inventory=device_inventory,
        account_security=account_security,
    )


@app.get("/customers/{user_id}/evidence-graph", response_model=EvidenceGraphResponse)
def get_evidence_graph(user_id: str, current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    prepare_analytics_tables(cursor)
    organization_id = current_user.organization_id or default_organization_id(cursor)
    cursor.execute("""
        SELECT COALESCE(NULLIF(device_id,''), device_type), ip, transaction_id, risk_level
        FROM events e
        LEFT JOIN fraud_alerts f ON f.organization_id=e.organization_id AND f.user_id=e.user_id
        WHERE e.organization_id=%s AND e.user_id=%s
        ORDER BY e.timestamp DESC LIMIT 50
    """, (organization_id, user_id))
    rows = cursor.fetchall()
    nodes = {"user": EvidenceNode(id=f"user:{user_id}", type="USER", label=user_id, risk="INFO")}
    edges = {}
    shared_accounts = set()
    for device, ip, transaction_id, risk_level in rows:
        for node_type, value in (("DEVICE", device), ("IP", ip), ("TRANSACTION", transaction_id)):
            if not value:
                continue
            node_id = f"{node_type.lower()}:{value}"
            nodes[node_id] = EvidenceNode(id=node_id, type=node_type, label=str(value), risk=risk_level or "LOW")
            edge_key = (f"user:{user_id}", node_id)
            edges[edge_key] = EvidenceEdge(source=edge_key[0], target=edge_key[1], relationship=f"USES_{node_type}", count=edges.get(edge_key, EvidenceEdge(source="", target="", relationship="")).count + (1 if edge_key in edges else 0))
        if device:
            cursor.execute("""
                SELECT DISTINCT user_id FROM events
                WHERE organization_id=%s AND user_id<>%s
                  AND COALESCE(NULLIF(device_id,''), device_type)=%s LIMIT 10
            """, (organization_id, user_id, device))
            shared_accounts.update(row[0] for row in cursor.fetchall())
        if ip:
            cursor.execute("SELECT DISTINCT user_id FROM events WHERE organization_id=%s AND user_id<>%s AND ip=%s LIMIT 10", (organization_id, user_id, ip))
            shared_accounts.update(row[0] for row in cursor.fetchall())
    for account in shared_accounts:
        node_id = f"user:{account}"
        nodes[node_id] = EvidenceNode(id=node_id, type="USER", label=account, risk="HIGH")
        edges[(f"user:{user_id}", node_id)] = EvidenceEdge(source=f"user:{user_id}", target=node_id, relationship="SHARED_IDENTITY")
    conn.close()
    return EvidenceGraphResponse(nodes=list(nodes.values()), edges=list(edges.values()), suspected_ring=len(shared_accounts) >= 2)


@app.patch("/customers/{user_id}/devices/{fingerprint}", response_model=DeviceProfileResponse)
def update_device_trust(
    user_id: str,
    fingerprint: str,
    payload: DeviceTrustUpdate,
    current_user: AuthUserResponse = Depends(get_current_user),
):
    if current_user.role not in {"Admin", "Fraud Analyst", "Investigator"}:
        raise HTTPException(status_code=403, detail="Your role cannot change device trust")
    conn, cursor = get_db()
    ensure_device_security_tables(cursor)
    organization_id = current_user.organization_id or default_organization_id(cursor)
    trust_score = {"NEW": 25, "TRUSTED": 90, "SUSPICIOUS": 15, "BLOCKED": 0}[payload.status]
    cursor.execute("""
        UPDATE device_fingerprints
        SET status = %s, trust_score = %s
        WHERE organization_id = %s AND user_id = %s AND fingerprint = %s
        RETURNING fingerprint, label, status, trust_score, first_seen_at, last_seen_at,
                  event_count, last_ip, last_location, integrity_flags
    """, (payload.status, trust_score, organization_id, user_id, fingerprint))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Device fingerprint not found")
    conn.commit()
    conn.close()
    return DeviceProfileResponse(
        fingerprint=row[0],
        label=row[1] or "Unknown device",
        status=row[2],
        trust_score=int(row[3] or 0),
        first_seen_at=str(row[4]),
        last_seen_at=str(row[5]),
        event_count=int(row[6] or 0),
        last_ip=row[7],
        last_location=row[8],
        integrity_flags=list(row[9] or []),
    )


@app.get("/intelligence/activity", response_model=IntelligenceActivityResponse)
def get_intelligence_activity(limit: int = Query(30), current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    ensure_case_tables(cursor)
    organization_id = current_user.organization_id or default_organization_id(cursor)
    materialize_cases_from_alerts(cursor, organization_id)
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
        WHERE c.organization_id = %s
        ORDER BY t.created_at DESC, t.id DESC
        LIMIT %s
    """, (organization_id, limit))
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
    organization_id = current_user.organization_id or default_organization_id(cursor)
    materialize_cases_from_alerts(cursor, organization_id)
    conn.commit()

    cursor.execute("""
        SELECT
            id,
            case_number,
            user_id,
            transaction_id,
            transaction_direction,
            risk_score,
            risk_level,
            confidence,
            recommended_action,
            status,
            priority,
            assigned_to,
            analyst_feedback,
            created_at,
            updated_at
        FROM cases
        WHERE organization_id = %s
          AND (%s IS NULL OR status = %s)
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
    """, (organization_id, status, status, priority, priority, analyst, analyst, risk_level, risk_level))
    rows = cursor.fetchall()
    conn.close()
    return [row_to_case_summary(row) for row in rows]


@app.get("/cases/{case_id}", response_model=CaseDetailResponse)
def get_case(case_id: int, current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    ensure_case_tables(cursor)
    organization_id = current_user.organization_id or default_organization_id(cursor)
    materialize_cases_from_alerts(cursor, organization_id)
    conn.commit()

    cursor.execute("""
        SELECT
            id,
            case_number,
            user_id,
            transaction_id,
            transaction_direction,
            risk_score,
            risk_level,
            confidence,
            recommended_action,
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
        WHERE id = %s AND organization_id = %s
    """, (case_id, organization_id))
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

    summary = row_to_case_summary(row[:15])
    reason = row[15] or ""
    return CaseDetailResponse(
        **summary.model_dump(),
        reason=reason,
        decision=row[17],
        potential_loss=float(row[18]) if row[18] is not None else None,
        actual_loss=float(row[19]) if row[19] is not None else None,
        fraud_signals=parse_reasons(reason),
        score_breakdown=build_score_breakdown(reason, row[5]),
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
    ensure_fraud_alert_table(cursor)
    ensure_risk_decision_table(cursor)
    organization_id = current_user.organization_id or default_organization_id(cursor)
    cursor.execute("""
        SELECT assigned_to, status, priority, analyst_feedback, decision, potential_loss, actual_loss, fraud_alert_id
        FROM cases
        WHERE id = %s AND organization_id = %s
    """, (case_id, organization_id))
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
    fraud_alert_id = before[7]

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
    params.append(organization_id)
    cursor.execute(f"UPDATE cases SET {', '.join(set_clauses)} WHERE id = %s AND organization_id = %s", params)

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

    feedback = changes.get("analyst_feedback")
    if feedback and fraud_alert_id:
        cursor.execute("""
            SELECT d.id, d.organization_id, d.user_id, d.request_payload, d.learned
            FROM fraud_alerts f
            JOIN risk_decisions d ON d.id = f.risk_decision_id
            WHERE f.id = %s
        """, (fraud_alert_id,))
        decision_row = cursor.fetchone()
        if decision_row:
            decision_id, organization_id, user_id, request_payload, learned = decision_row
            cursor.execute("""
                UPDATE risk_decisions
                SET analyst_feedback = %s, feedback_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (feedback, decision_id))
            learned_features = []
            if feedback == "FALSE_POSITIVE" and not learned:
                update_behavior_profile(
                    cursor,
                    organization_id or default_organization_id(cursor),
                    user_id,
                    request_payload,
                    trusted=True,
                    increment_event=False,
                )
                cursor.execute("UPDATE risk_decisions SET learned = TRUE WHERE id = %s", (decision_id,))
                learned_features = ["trusted_behavior_baseline"]
            elif feedback == "TRUE_FRAUD":
                ensure_decision_rule_tables(cursor)
                cursor.execute("SELECT enabled, share_devices, share_ips FROM consortium_settings WHERE organization_id = %s", (organization_id,))
                consortium = cursor.fetchone()
                if consortium and consortium[0]:
                    entities = []
                    if consortium[1]:
                        entities.append(("DEVICE", device_fingerprint(request_payload)))
                    if consortium[2] and request_payload.get("ip"):
                        entities.append(("IP", request_payload["ip"]))
                    for entity_type, value in entities:
                        cursor.execute("""
                            INSERT INTO consortium_reputation (entity_type, entity_hash, organization_id, confirmed_fraud_count)
                            VALUES (%s, %s, %s, 1)
                            ON CONFLICT (entity_type, entity_hash, organization_id)
                            DO UPDATE SET confirmed_fraud_count = consortium_reputation.confirmed_fraud_count + 1,
                                          last_seen_at = CURRENT_TIMESTAMP
                        """, (entity_type, reputation_hash(entity_type, value), organization_id))
                    learned_features = [entity_type.lower() for entity_type, _ in entities]
            cursor.execute("""
                INSERT INTO feedback_learning_events (organization_id, risk_decision_id, feedback, learned_features)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (risk_decision_id, feedback) DO NOTHING
            """, (organization_id, decision_id, feedback, Json(learned_features)))

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
    organization_id = current_user.organization_id or default_organization_id(cursor)
    cursor.execute("SELECT id FROM cases WHERE id = %s AND organization_id = %s", (case_id, organization_id))
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


def perform_case_action(
    case_id: int,
    new_status: str,
    action_taken: str,
    current_user: AuthUserResponse,
    note: str | None = None,
    feedback: str | None = None,
    decision: str | None = None,
) -> CaseActionResponse:
    conn, cursor = get_db()
    ensure_case_tables(cursor)
    organization_id = current_user.organization_id or default_organization_id(cursor)
    cursor.execute("""
        SELECT id, status, transaction_id, user_id, fraud_alert_id
        FROM cases
        WHERE id = %s AND organization_id = %s
    """, (case_id, organization_id))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Case not found")

    _, previous_status, transaction_id, user_id, fraud_alert_id = row
    set_clauses = ["status = %s", "updated_at = CURRENT_TIMESTAMP"]
    params = [new_status]
    if feedback:
        set_clauses.append("analyst_feedback = %s")
        params.append(feedback)
    if decision:
        set_clauses.append("decision = %s")
        params.append(decision)
    if note:
        set_clauses.append("analyst_note = %s")
        params.append(note)
    if new_status in {"CONFIRMED_FRAUD", "FALSE_POSITIVE", "REVERSED", "CLOSED", "RESOLVED"}:
        set_clauses.append("resolved_at = COALESCE(resolved_at, CURRENT_TIMESTAMP)")
    if new_status == "REVERSED":
        set_clauses.append("reversed_at = CURRENT_TIMESTAMP")
    params.extend([case_id, organization_id])
    cursor.execute(f"""
        UPDATE cases
        SET {', '.join(set_clauses)}
        WHERE id = %s AND organization_id = %s
    """, params)

    if note:
        cursor.execute("""
            INSERT INTO case_notes (case_id, author, note)
            VALUES (%s, %s, %s)
        """, (case_id, current_user.name, note))
    timeline(cursor, case_id, action_taken, f"{action_taken.replace('_', ' ').title()} by {current_user.name}", current_user.name)
    audit_log(cursor, organization_id, case_id, transaction_id, user_id, action_taken, previous_status, new_status, note)

    if feedback and fraud_alert_id:
        cursor.execute("""
            UPDATE risk_decisions d
            SET analyst_feedback = %s, feedback_at = CURRENT_TIMESTAMP
            FROM fraud_alerts f
            WHERE f.risk_decision_id = d.id AND f.id = %s
        """, (feedback, fraud_alert_id))

    conn.commit()
    conn.close()
    return CaseActionResponse(
        message={
            "CASE_REVIEWED": "Case moved to analyst review",
            "CONFIRMED_FRAUD": "Case confirmed as fraud",
            "MARKED_FALSE_POSITIVE": "Case marked as false positive",
            "REVERSED": "Transaction restriction reversed successfully",
            "CLOSED": "Case closed successfully",
        }.get(action_taken, "Case updated successfully"),
        case_id=str(case_id),
        transaction_id=transaction_id,
        status=new_status,
    )


@app.post("/cases/{case_id}/review", response_model=CaseActionResponse)
def review_case(case_id: int, payload: CaseActionRequest, current_user: AuthUserResponse = Depends(get_current_user)):
    return perform_case_action(case_id, "UNDER_REVIEW", "CASE_REVIEWED", current_user, payload.analyst_note)


@app.post("/cases/{case_id}/confirm-fraud", response_model=CaseActionResponse)
def confirm_case_fraud(case_id: int, payload: CaseActionRequest, current_user: AuthUserResponse = Depends(get_current_user)):
    return perform_case_action(case_id, "CONFIRMED_FRAUD", "CONFIRMED_FRAUD", current_user, payload.analyst_note, "TRUE_FRAUD", "PND_OR_BLOCK")


@app.post("/cases/{case_id}/false-positive", response_model=CaseActionResponse)
def mark_case_false_positive(case_id: int, payload: CaseActionRequest, current_user: AuthUserResponse = Depends(get_current_user)):
    return perform_case_action(case_id, "FALSE_POSITIVE", "MARKED_FALSE_POSITIVE", current_user, payload.analyst_note, "FALSE_POSITIVE", "ALLOW")


@app.post("/cases/{case_id}/reverse", response_model=CaseActionResponse)
def reverse_case_restriction(case_id: int, payload: CaseActionRequest, current_user: AuthUserResponse = Depends(get_current_user)):
    return perform_case_action(case_id, "REVERSED", "REVERSED", current_user, payload.analyst_note, "FALSE_POSITIVE", "ALLOW")


@app.post("/cases/{case_id}/close", response_model=CaseActionResponse)
def close_case(case_id: int, payload: CaseActionRequest, current_user: AuthUserResponse = Depends(get_current_user)):
    return perform_case_action(case_id, "CLOSED", "CLOSED", current_user, payload.analyst_note)


@app.get("/audit-logs", response_model=list[AuditLogResponse])
def get_audit_logs(limit: int = Query(100), current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    ensure_case_tables(cursor)
    organization_id = current_user.organization_id or default_organization_id(cursor)
    cursor.execute("""
        SELECT id, case_id, transaction_id, user_id, action_taken,
               previous_status, new_status, analyst_note, created_at
        FROM fraud_audit_logs
        WHERE organization_id = %s
        ORDER BY id DESC
        LIMIT %s
    """, (organization_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return [
        AuditLogResponse(
            id=row[0],
            case_id=row[1],
            transaction_id=row[2],
            user_id=row[3],
            action_taken=row[4],
            previous_status=row[5],
            new_status=row[6],
            analyst_note=row[7],
            created_at=str(row[8]),
        )
        for row in rows
    ]


@app.get("/analytics/overview", response_model=AnalyticsOverviewResponse)
def analytics_overview(current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    prepare_analytics_tables(cursor)
    conn.commit()
    organization_id = current_user.organization_id or default_organization_id(cursor)

    cursor.execute("SELECT COUNT(*) FROM events WHERE organization_id = %s", (organization_id,))
    total_events = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM fraud_alerts WHERE organization_id = %s", (organization_id,))
    fraud_alerts = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM cases WHERE organization_id = %s AND analyst_feedback = 'TRUE_FRAUD'", (organization_id,))
    confirmed = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM cases WHERE organization_id = %s AND analyst_feedback = 'FALSE_POSITIVE'", (organization_id,))
    false_positive = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM cases WHERE organization_id = %s AND status = 'RESOLVED'", (organization_id,))
    resolved = cursor.fetchone()[0]
    cursor.execute("""
        SELECT AVG(EXTRACT(EPOCH FROM (COALESCE(resolved_at, updated_at) - created_at)) / 60)
        FROM cases
        WHERE organization_id = %s AND status IN ('RESOLVED', 'ARCHIVED')
    """, (organization_id,))
    avg_minutes = cursor.fetchone()[0] or 0
    cursor.execute("""
        SELECT COUNT(*) FROM cases
        WHERE organization_id = %s
          AND (decision IN ('BLOCK', 'FREEZE', 'ESCALATE') OR COALESCE(actual_loss, 0) = 0)
    """, (organization_id,))
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
    organization_id = current_user.organization_id or default_organization_id(cursor)
    cursor.execute("""
        SELECT COALESCE(DATE(timestamp)::TEXT, 'Unknown') AS day, COUNT(*)
        FROM fraud_alerts
        WHERE organization_id = %s
        GROUP BY day
        ORDER BY day
        LIMIT 30
    """, (organization_id,))
    rows = cursor.fetchall()
    conn.close()
    return [TrendPointResponse(label=r[0], value=r[1]) for r in rows]


@app.get("/analytics/risk-distribution", response_model=list[RiskDistributionResponse])
def analytics_risk_distribution(current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    prepare_analytics_tables(cursor)
    conn.commit()
    organization_id = current_user.organization_id or default_organization_id(cursor)
    cursor.execute("""
        SELECT risk_level, COUNT(*)
        FROM fraud_alerts
        WHERE organization_id = %s
        GROUP BY risk_level
    """, (organization_id,))
    rows = cursor.fetchall()
    conn.close()
    counts = {r[0] or "LOW": r[1] for r in rows}
    return [RiskDistributionResponse(level=level, count=counts.get(level, 0)) for level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")]


@app.get("/analytics/analyst-performance", response_model=list[AnalystPerformanceResponse])
def analytics_analyst_performance(current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    prepare_analytics_tables(cursor)
    conn.commit()
    organization_id = current_user.organization_id or default_organization_id(cursor)
    cursor.execute("""
        SELECT
            COALESCE(assigned_to, 'Unassigned') AS analyst,
            COUNT(*) AS assigned_cases,
            COUNT(*) FILTER (WHERE status IN ('RESOLVED', 'ARCHIVED')) AS resolved_cases,
            COUNT(*) FILTER (WHERE analyst_feedback = 'TRUE_FRAUD') AS confirmed_fraud,
            COUNT(*) FILTER (WHERE analyst_feedback = 'FALSE_POSITIVE') AS false_positives
        FROM cases
        WHERE organization_id = %s
        GROUP BY analyst
        ORDER BY assigned_cases DESC
        LIMIT 12
    """, (organization_id,))
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
    organization_id = current_user.organization_id or default_organization_id(cursor)
    cursor.execute("""
        SELECT
            COALESCE(NULLIF(e.location, ''), 'Unknown') AS location,
            COUNT(DISTINCT f.id) AS alerts,
            COALESCE(AVG(f.risk_score), 0) AS average_risk,
            COALESCE(MAX(f.risk_level), 'LOW') AS highest_risk
        FROM fraud_alerts f
        LEFT JOIN events e ON e.user_id = f.user_id AND e.organization_id = f.organization_id
        WHERE f.organization_id = %s
        GROUP BY location
        ORDER BY alerts DESC, average_risk DESC
        LIMIT 16
    """, (organization_id,))
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
    organization_id = current_user.organization_id or default_organization_id(cursor)
    cursor.execute("""
        SELECT user_id, risk_score, risk_level, recommended_action, confidence, timestamp
        FROM fraud_alerts
        WHERE organization_id = %s
        ORDER BY timestamp DESC NULLS LAST, id DESC
    """, (organization_id,))
    rows = cursor.fetchall()
    conn.close()
    return csv_response("fraud-alerts.csv", ["user_id", "risk_score", "risk_level", "action", "confidence", "time"], rows)


@app.get("/export/cases.csv")
def export_cases(current_user: AuthUserResponse = Depends(get_current_user)):
    conn, cursor = get_db()
    prepare_analytics_tables(cursor)
    conn.commit()
    organization_id = current_user.organization_id or default_organization_id(cursor)
    cursor.execute("""
        SELECT case_number, user_id, risk_score, risk_level, status, priority, assigned_to, analyst_feedback, decision, potential_loss, actual_loss, created_at, updated_at
        FROM cases
        WHERE organization_id = %s
        ORDER BY updated_at DESC, id DESC
    """, (organization_id,))
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
    organization_id = current_user.organization_id or default_organization_id(cursor)
    cursor.execute("""
        SELECT
            COALESCE(DATE_TRUNC('month', created_at)::DATE::TEXT, 'Unknown') AS month,
            COUNT(*) AS cases,
            COUNT(*) FILTER (WHERE analyst_feedback = 'TRUE_FRAUD') AS confirmed_fraud,
            COUNT(*) FILTER (WHERE analyst_feedback = 'FALSE_POSITIVE') AS false_positives,
            COUNT(*) FILTER (WHERE status IN ('RESOLVED', 'ARCHIVED')) AS resolved
        FROM cases
        WHERE organization_id = %s
        GROUP BY month
        ORDER BY month DESC
    """, (organization_id,))
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
def get_features(limit: int = 50, current_user: AuthUserResponse = Depends(get_current_user)):
    require_admin(current_user)
    conn, cursor = get_db()
    cursor.execute("SELECT slug FROM organizations WHERE id = %s", (current_user.organization_id,))
    organization = cursor.fetchone()
    if not organization or organization[0] != "boujuron":
        conn.close()
        raise HTTPException(status_code=403, detail="Platform administrator access required")

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
