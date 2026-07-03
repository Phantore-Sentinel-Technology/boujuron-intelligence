# Boujuron Intelligence

**Boujuron Intelligence** is an Africa-focused **fraud intelligence API and banking-grade fraud operations platform** for fintechs, digital wallets, payment companies, marketplaces, SaaS products, and financial institutions.

Boujuron helps organizations score risky activity in real time, detect abnormal customer behavior, apply balanced fraud decisions, protect funds through automatic PND/block controls for critical threats, and give analysts a clear investigation workflow for review, reversal, closure, and audit.

The platform has evolved from a fraud dashboard into a real-time fraud decisioning and operations system.

---

## Product Positioning

Boujuron is designed to answer one operational question:

> Should this activity be allowed, challenged, held for review, or blocked immediately?

The platform receives login, wallet, transaction, device, and behavioral events, then returns a structured fraud decision containing:

- Risk score
- Risk level
- Confidence
- Recommended action
- Human-readable reasons
- Triggered signals
- Device intelligence
- Account takeover indicators
- Case and audit records where required

Boujuron is built for teams that need to reduce fraud losses without creating unnecessary friction for legitimate customers.

---

## Current Version

Boujuron V2 is focused on **banking-grade fraud protection** and supports:

- Debit and credit transaction monitoring
- Real-time risk scoring API
- Balanced decisioning model
- Auto-PND/block for critical, high-confidence fraud
- Analyst review for medium and high-risk cases
- Reversal workflow for false positives
- Audit trail for major fraud decisions
- User risk profiles
- Device fingerprinting
- Account takeover detection
- Bot attack detection
- Behavioral intelligence
- Fraud playbooks
- Investigation timeline
- Case management
- Executive analytics
- CSV/PDF reporting
- Fraud heat map
- Invite-only authentication
- API keys and customer portal foundation
- Multi-tenant organization isolation foundation
- Consortium intelligence foundation

---

## Why Boujuron Exists

Fraud teams in fintech and banking environments face pressure from:

- Account takeovers
- SIM swap indicators
- New-device fraud
- Credential stuffing
- Bot-driven login and registration abuse
- Suspicious inflows
- Repetitive outflows
- Mule account movement
- Dormant accounts suddenly receiving large funds
- Large transfers after security changes
- VPN, proxy, TOR, emulator, and rooted-device usage
- Manual review backlogs
- Slow response during mass-fraud incidents

Traditional dashboards only show alerts. Boujuron is designed to help institutions **detect, decide, act, review, and audit** from one platform.

---

## Decision Model

Boujuron separates **risk score** from **confidence**.

- **Risk score** measures how severe the detected behavior is.
- **Confidence** measures how certain the platform is that the decision is correct.

This distinction is important because not every unusual transaction should be blocked.

| Risk Level | Meaning | Default Action |
| ---------- | ------- | -------------- |
| LOW | Normal or trusted activity | `ALLOW` |
| MEDIUM | Some suspicious indicators | `STEP_UP_VERIFY` |
| HIGH | Strong suspicious indicators | `HOLD_FOR_REVIEW` |
| CRITICAL | Severe multi-signal fraud confidence | `PND_OR_BLOCK` |

Boujuron follows a balanced fraud principle:

> Only highly confident fraud should trigger hard blocking or PND. Moderate risk should go through verification or analyst review. Low risk should be allowed.

---

## Debit and Credit Fraud Rules

Boujuron treats money leaving and money entering an account differently.

### Debit Monitoring

Debit rules focus on outgoing fraud risk:

- Unusual transaction amount
- New or suspicious device
- Blacklisted IP
- VPN, TOR, proxy, emulator, or rooted device
- Unusual login or transaction time
- Multiple failed login attempts
- Recent password reset
- SIM change before transaction
- New beneficiary before large transfer
- High transaction velocity
- Repetitive outflows
- Sudden behavior change from customer profile

### Credit Monitoring

Credit rules focus on incoming-fund risk:

- Unusual incoming amount
- Multiple rapid credits from different sources
- Credits followed quickly by suspicious debits
- Suspicious sender or channel pattern
- Mule-account behavior
- Dormant account suddenly receiving large credits
- Unusual credit frequency
- High-risk inflow channels
- Reversal or chargeback risk indicators

Rule modules are separated for readability and growth:

```text
services/risk_engine_service/debit_rules.py
services/risk_engine_service/credit_rules.py
services/risk_engine_service/shared_rules.py
services/risk_engine_service/engine.py
```

---

## Real-Time Fraud Intelligence API

Boujuron can be integrated directly into a fintech's login, wallet, transaction, or payment workflow.

### Endpoint

```http
POST /risk-score
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
Idempotency-Key: transaction-unique-key
```

Client API-key support is also available for customer integrations:

```http
POST /risk-score
X-API-Key: bj_live_your_secret_key
Idempotency-Key: transaction-unique-key
Content-Type: application/json
```

### Example Debit Request

```json
{
  "transaction_id": "debit_001",
  "user_id": "customer_101",
  "transaction_direction": "DEBIT",
  "amount": 500000,
  "event_type": "wallet_transfer",
  "device_type": "android",
  "device_id": "device-a19",
  "ip": "102.88.45.21",
  "location": "lagos, nigeria",
  "network": "MOBILE",
  "failed_login_count": 0,
  "password_changed_recently": false,
  "sim_swap_detected": false,
  "new_beneficiary_added": false
}
```

### Example Credit Request

```json
{
  "transaction_id": "credit_001",
  "user_id": "customer_301",
  "transaction_direction": "CREDIT",
  "amount": 2500000,
  "event_type": "credit",
  "device_type": "unknown device",
  "device_id": "device-credit-301",
  "ip": "102.88.45.31",
  "location": "port harcourt, nigeria",
  "network": "MOBILE",
  "account_age_days": 2,
  "dormant_account": true,
  "rapid_credit_count": 4
}
```

### Example Response

```json
{
  "decision_id": 42,
  "user_id": "customer_301",
  "transaction_id": "credit_001",
  "transaction_direction": "CREDIT",
  "risk_score": 100,
  "risk_level": "CRITICAL",
  "action": "PND_OR_BLOCK",
  "recommendation": "PND_OR_BLOCK",
  "confidence": 99,
  "reasons": [
    "Very large incoming credit",
    "Dormant account large credit",
    "Suspicious device: unknown device"
  ],
  "signals": [
    {
      "category": "CREDIT",
      "label": "Very large incoming credit",
      "points": 35,
      "evidence": "Incoming credit exceeded configured high-value threshold"
    }
  ],
  "behavioral_match": false,
  "device_intelligence": {
    "status": "NEW",
    "trust_score": 25,
    "is_new_device": true
  },
  "account_takeover": {
    "detected": false,
    "score": 0,
    "level": "LOW",
    "indicators": []
  },
  "created_at": "2026-06-30 13:43:12"
}
```

---

## Automatic PND and Analyst Review

Boujuron does not wait for analysts when a transaction is critical and highly confident.

For `CRITICAL` decisions:

- Recommended action becomes `PND_OR_BLOCK`
- Transaction is treated as temporarily blocked or restricted
- A fraud case is opened automatically
- Audit log records `TRANSACTION_BLOCKED`
- Timeline records `AUTO_PND_APPLIED`
- Analyst can later confirm fraud or reverse the restriction

For `HIGH` decisions:

- Recommended action becomes `HOLD_FOR_REVIEW`
- Case is opened for analyst review
- Analyst decides whether to confirm fraud, mark false positive, reverse, or close

For `MEDIUM` decisions:

- Recommended action becomes `STEP_UP_VERIFY`
- Customer may be challenged with OTP, PIN, MFA, or additional verification

For `LOW` decisions:

- Activity is allowed and monitored

---

## Case Management and Reversal Workflow

Boujuron creates investigation cases when activity requires review or restriction.

Case statuses include:

- `OPEN`
- `UNDER_REVIEW`
- `CONFIRMED_FRAUD`
- `FALSE_POSITIVE`
- `REVERSED`
- `CLOSED`

Supported case actions include:

```http
GET  /cases
GET  /cases/{case_id}
POST /cases/{case_id}/review
POST /cases/{case_id}/confirm-fraud
POST /cases/{case_id}/false-positive
POST /cases/{case_id}/reverse
POST /cases/{case_id}/close
```

The reversal workflow is important for fair customer treatment. If an analyst determines a held or blocked transaction is legitimate, the restriction can be reversed and logged.

Example reversal response:

```json
{
  "message": "Transaction restriction reversed successfully",
  "case_id": "CASE-0012",
  "transaction_id": "credit_005",
  "status": "REVERSED"
}
```

---

## Audit Trail

Every major decision is auditable.

Boujuron records actions such as:

- `CASE_CREATED`
- `TRANSACTION_HELD`
- `TRANSACTION_BLOCKED`
- `AUTO_PND_APPLIED`
- `CASE_REVIEWED`
- `CONFIRMED_FRAUD`
- `MARKED_FALSE_POSITIVE`
- `REVERSED`
- `CLOSED`

Audit data supports fraud operations, compliance reviews, internal investigations, and client reporting.

---

## Dashboard and Investigation Console

The React dashboard is the fraud operations command center.

It includes:

- Real-time alert queue
- Risk score movement chart
- Risk mix distribution
- Live activity feed
- Notification bell
- Case status visibility
- Inline analyst actions
- Investigation drawer
- User risk profiles
- Executive analytics
- CSV export
- PDF fraud reports
- Fraud heat map
- History page
- Dark/light mode
- Mobile-responsive layout

### Investigation Drawer

The drawer gives analysts the full story of a risk decision:

- Customer ID
- Transaction ID
- Direction: `DEBIT` or `CREDIT`
- Risk score
- Risk level
- Confidence
- Recommended action
- Closure status
- Closure note
- Why the decision was made
- Explainable score breakdown
- Timeline of events
- Fraud playbook
- Case/audit context

### Fraud Playbooks

Boujuron guides analysts with recommended next steps for:

- Account takeover
- Bot attack
- Suspicious inflow
- Repetitive outflow
- Manipulated device
- General fraud review

---

## User Risk Profiles

Each customer profile can show:

- Current risk score
- Risk trend
- Recent events
- Known devices
- New devices
- Known locations
- IP history
- Behavioral profile
- Device trust inventory
- Account takeover state
- Risk timeline
- Previous investigations
- Evidence graph

This helps analysts understand the customer story, not just a single transaction.

---

## Behavioral Intelligence

Boujuron maintains organization-scoped behavioral baselines, including:

- Average transaction amount
- Trusted device fingerprints
- Trusted location history
- Normal activity-hour distribution
- Login and transaction velocity windows
- Event frequency
- Historical risk movement

Behavioral scoring is designed to avoid unfairly punishing new customers with limited history. Low-risk events can strengthen a profile, while high-risk activity is not automatically treated as normal.

Admins can configure baseline behavior in the settings area, including:

- Amount spike multiplier
- New device/location sensitivity
- Activity-hour sensitivity
- Velocity window
- Event limits
- Adaptive learning controls

---

## Authentication and Access Control

Boujuron uses controlled platform access.

Supported access features:

- Invite-only registration
- 24-hour invite tokens
- Login and logout
- JWT authentication
- Password reset
- Role-based access
- Organization isolation foundation

Supported roles:

```text
Admin
Fraud Analyst
Investigator
Read-Only Auditor
```

---

## Architecture

Current production architecture:

```text
Client / Dashboard / Partner System
              |
              v
      FastAPI Dashboard API
              |
              v
       Risk Engine Service
              |
              v
  Debit Rules | Credit Rules | Shared Rules
              |
              v
    PostgreSQL / Supabase Database
              |
              v
 React Fraud Operations Dashboard
```

Local distributed architecture also supports:

```text
Client Platforms
      |
      v
Event Ingestion Service
      |
      v
Kafka / Redpanda Stream
      |
      v
Consumers and Fraud Alert Workers
      |
      v
Risk Engine and PostgreSQL
      |
      v
Dashboard API and React Console
```

---

## Technology Stack

| Layer | Technology |
| ----- | ---------- |
| Frontend | React, TypeScript, Vite, Recharts, Lucide Icons |
| Backend API | Python, FastAPI, Pydantic |
| Risk Engine | Python rule modules and behavioral scoring |
| Database | PostgreSQL / Supabase-compatible Postgres |
| Streaming | Kafka / Redpanda for local distributed mode |
| Authentication | JWT, invite tokens, role-based access |
| Reports | CSV and PDF exports |
| Deployment | Docker, Fly.io |
| Local Dev | Docker Compose |
| Testing | Pytest, TypeScript build |

---

## Project Structure

```text
boujuron-intelligence/
|
+-- config/
|   +-- settings.py
|
+-- db/
|   +-- init.sql
|
+-- docs/
|   +-- BRD.md
|   +-- FRD.md
|   +-- architecture.md
|
+-- frontend/
|   +-- public/
|   +-- src/
|   |   +-- components/
|   |   +-- hooks/
|   |   +-- pages/
|   |   +-- services/
|   |   +-- utils/
|   |   +-- types.ts
|   +-- package.json
|
+-- infrastructure/
|   +-- fraud_alert_service/
|   +-- kafka_consumer/
|   +-- ml/
|   +-- risk_engine/
|
+-- services/
|   +-- dashboard_service/
|   |   +-- main.py
|   |   +-- schemas.py
|   +-- event_ingestion_service/
|   +-- risk_engine_service/
|       +-- credit_rules.py
|       +-- debit_rules.py
|       +-- engine.py
|       +-- schemas.py
|       +-- shared_rules.py
|
+-- tests/
+-- docker-compose.yml
+-- Dockerfile
+-- fly.toml
+-- requirements-dashboard.txt
+-- README.md
```

---

## Important API Endpoints

| Method | Endpoint | Purpose |
| ------ | -------- | ------- |
| `POST` | `/auth/login` | Authenticate users |
| `POST` | `/auth/register` | Register with invite token |
| `POST` | `/auth/invites` | Generate invite token |
| `POST` | `/auth/forgot-password` | Request password reset |
| `POST` | `/auth/reset-password` | Reset password |
| `POST` | `/risk-score` | Score a transaction or behavioral event |
| `GET` | `/fraud-alerts` | Fetch dashboard alerts |
| `GET` | `/events` | Fetch event history |
| `GET` | `/cases` | Fetch fraud cases |
| `GET` | `/cases/{case_id}` | Fetch case detail |
| `POST` | `/cases/{case_id}/reverse` | Reverse a restriction |
| `GET` | `/audit-logs` | Fetch audit logs |
| `GET` | `/customers/{user_id}/profile` | Fetch customer risk profile |
| `GET` | `/customers/{user_id}/evidence-graph` | Fetch customer evidence graph |
| `GET` | `/analytics/overview` | Executive KPI overview |
| `GET` | `/export/fraud-alerts.csv` | Export alerts CSV |
| `GET` | `/reports/monthly.pdf` | Generate PDF report |

---

## Environment Variables

Typical production variables:

```env
ENVIRONMENT=production
DATABASE_URL=postgresql://USER:PASSWORD@HOST:PORT/DATABASE
JWT_SECRET=replace-with-long-random-secret
FRONTEND_URL=https://your-domain.com
CORS_ORIGINS=https://your-domain.com
KAFKA_BOOTSTRAP_SERVER=
RISK_ENGINE_API=
```

Frontend variables when hosted separately:

```env
VITE_API_URL=https://your-api-domain.com
VITE_WS_URL=wss://your-api-domain.com/ws/fraud
```

---

## Running Locally With Docker

Prerequisites:

- Docker
- Docker Compose
- Python 3.11+
- Node.js 22+

Start the local distributed stack:

```bash
docker compose up --build
```

The dashboard service is exposed locally on:

```text
http://localhost:8002
```

Other local services:

```text
Event ingestion: http://localhost:8000
Risk engine:     http://localhost:8001
Fraud alert:     http://localhost:8003
PostgreSQL:      localhost:5432
Redpanda/Kafka:  localhost:9092
```

---

## Running Frontend Locally

```bash
cd frontend
npm install
npm run dev
```

Build production frontend:

```bash
cd frontend
npm run build
```

---

## Running Backend Tests

Focused banking fraud tests:

```bash
./venv/bin/python -m pytest tests/test_banking_fraud_engine.py tests/test_decision_rules.py
```

Full test suite:

```bash
./venv/bin/python -m pytest
```

---

## Deployment

Boujuron is currently deployable as a Dockerized FastAPI + React application.

Production deployment target:

```text
Fly.io
```

Current Fly configuration:

```text
App: boujuron-intelligence
Primary region: iad
Internal port: 8000
```

Deploy:

```bash
flyctl deploy
```

Health check:

```http
GET /health
```

Expected response:

```json
{
  "status": "ok",
  "service": "boujuron-dashboard-api"
}
```

---

## Business Documentation

The project includes product and functional documentation:

- `docs/BRD.md` - Business Requirements Document
- `docs/FRD.md` - Functional Requirements Document
- `docs/architecture.md` - Architecture notes

These documents explain the banking fraud problem, customer pain points, fraud workflows, API behavior, dashboard expectations, and operational value.

---

## Security Principles

Boujuron is designed around the following principles:

- Controlled invite-only access
- JWT authentication
- Role-based access
- Organization data isolation foundation
- API key support for client integrations
- Audit logs for major fraud actions
- PND/block only for high-confidence critical events
- Reversal support for false positives
- Secure handling of customer event data

---

## Product Vision

Boujuron's long-term vision is to become the **fraud intelligence infrastructure layer for African fintechs and financial institutions**.

The roadmap moves through four major layers:

1. **Risk Scoring API** - real-time event scoring and fraud decisions.
2. **Fraud Operations Console** - analyst workflow, cases, playbooks, reversal, and audit.
3. **Customer Intelligence Layer** - user profiles, device trust, behavior baselines, and evidence graph.
4. **Fraud Consortium Network** - privacy-safe shared intelligence across participating institutions.

The strategic differentiator is not only fraud detection. It is Africa-native fraud decisioning, operational workflow, and shared intelligence built around the fraud patterns local financial platforms face every day.

---

## Founding Team

**Iniobong Udoette**  
Founder and Product Lead

Responsible for product strategy, market development, client relationships, and partnerships.

**Olabowale Babatunde Ipaye**  
Chief Technology Officer

Responsible for product architecture, backend platform development, frontend implementation, infrastructure, and technical delivery.

---

## License

This project is proprietary software owned by the Boujuron / Phantore Sentinel team.

Unauthorized copying, distribution, modification, or commercial use is not permitted without written permission.
