# Boujuron Intelligence

**Boujuron Intelligence** is an Africa-focused **fraud intelligence API, real-time risk decision engine, and banking fraud operations platform** built for fintechs, digital wallets, payment companies, marketplaces, SaaS platforms, and financial institutions.

Boujuron helps organizations detect suspicious activity early, score debit and credit transactions in real time, apply balanced fraud decisions, trigger account-level protection for critical threats, and give analysts a complete workflow for investigation, reversal, closure, and audit.

This project is being submitted for a hackathon as a working product prototype and technical foundation for a larger vision: **Africa-native fraud intelligence infrastructure for modern financial platforms**.

---

## Hackathon Summary

Fraud teams do not only need another dashboard. They need a system that can answer:

> Should this customer activity be allowed, challenged, held for review, or blocked immediately?

Boujuron addresses that by combining:

- A real-time **Fraud Intelligence API**
- Banking-focused **debit and credit risk rules**
- **Behavioral intelligence** and user risk profiles
- **Device fingerprinting** and account takeover indicators
- **Bot attack and credential stuffing detection**
- **Automatic PND/block logic** for critical high-confidence cases
- A fraud operations dashboard for analysts and managers
- Case review, false-positive handling, reversal, closure, and audit logs
- Executive analytics, exports, and reporting
- A foundation for multi-tenant customer isolation and consortium intelligence

Boujuron is designed to protect customers and institutions while reducing unnecessary friction for legitimate activity.

---

## The Problem

African fintechs, wallets, and payment platforms face fast-moving fraud patterns such as:

- Account takeovers
- SIM swap and new-device fraud
- Credential stuffing and bot attacks
- Suspicious inflows
- Repetitive outflows
- Mule account movement
- Dormant accounts suddenly receiving large credits
- Large transfers after password reset or SIM change
- VPN, TOR, proxy, emulator, and rooted-device usage
- Analyst overload during mass-fraud events
- Slow manual response when funds need to be protected immediately

Traditional dashboards can show alerts, but they often leave the hardest question unanswered: **what should the system do right now?**

Boujuron is built around decisioning, not just visibility.

---

## Product Positioning

Boujuron is a **fraud decisioning and operations layer** that can sit inside a financial platform's login, wallet, debit, credit, transfer, beneficiary, and account-management workflows.

When a client platform sends an event, Boujuron returns:

- `risk_score`
- `risk_level`
- `confidence`
- `recommended_action`
- Human-readable reasons
- Triggered signals
- Device intelligence
- Account takeover indicators
- Case/audit metadata where required

Boujuron's default decision model:

| Risk Level | Meaning | Default Action | Operational Handling |
| ---------- | ------- | -------------- | -------------------- |
| LOW | Normal or trusted activity | `ALLOW` | Stored in history, not shown in the analyst dashboard queue |
| MEDIUM | Suspicious but not severe | `STEP_UP_VERIFY` | Customer verification or analyst attention |
| HIGH | Strong suspicious indicators | `HOLD_FOR_REVIEW` | Case opened for review |
| CRITICAL | Extreme multi-signal fraud confidence | `PND_OR_BLOCK` | Account-level PND/block protection is applied, then analyst can confirm or reverse |

Important principle:

> Boujuron should not be a harsh blocking system. It should protect customers and financial institutions while reducing unnecessary customer friction. Only extreme, high-confidence fraud should trigger account-level PND/block.

---

## Current Feature Set

### Real-Time Fraud Intelligence API

Boujuron exposes a risk-scoring API that client systems can call before allowing sensitive activity.

```http
POST /risk-score
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
Idempotency-Key: transaction-unique-key
```

Client API-key integrations are also supported:

```http
POST /risk-score
X-API-Key: bj_live_your_secret_key
Idempotency-Key: transaction-unique-key
Content-Type: application/json
```

Example response:

```json
{
  "decision_id": 42,
  "transaction_id": "debit_001",
  "user_id": "customer_101",
  "transaction_direction": "DEBIT",
  "risk_score": 96,
  "risk_level": "CRITICAL",
  "confidence": 99,
  "recommended_action": "PND_OR_BLOCK",
  "reasons": [
    "New device after password reset",
    "SIM swap indicator",
    "Large transfer attempt",
    "Blacklisted IP",
    "VPN usage detected"
  ],
  "signals": [
    {
      "category": "ACCOUNT_TAKEOVER",
      "label": "New device after password reset",
      "points": 30
    }
  ],
  "behavioral_match": false,
  "created_at": "2026-07-18T10:30:00Z"
}
```

### Debit and Credit Transaction Monitoring

Boujuron treats money leaving an account and money entering an account differently.

**Debit monitoring** checks for:

- Unusual outgoing amount
- New or suspicious device
- Blacklisted IP
- VPN, TOR, proxy, emulator, or rooted device
- Unusual login or transaction time
- Failed login bursts
- Recent password reset
- SIM change before transaction
- New beneficiary before large transfer
- High transaction velocity
- Repetitive outflows
- Sudden change from customer profile

**Credit monitoring** checks for:

- Unusual incoming amount
- Multiple rapid credits from different sources
- Credits followed quickly by suspicious debits
- Suspicious sender/channel pattern
- Mule-account behavior
- Dormant account suddenly receiving large credits
- Unusual credit frequency
- High-risk inflow channels
- Reversal or chargeback risk indicators

Rule modules are organized for maintainability:

```text
services/risk_engine_service/debit_rules.py
services/risk_engine_service/credit_rules.py
services/risk_engine_service/shared_rules.py
services/risk_engine_service/engine.py
```

### Account-Level PND / Block Logic

Boujuron's latest workflow focuses on account protection, not just transaction labels.

For `CRITICAL` decisions:

- Boujuron applies account-level PND/block recommendation
- The risky transaction is treated as restricted
- A fraud case is opened automatically
- Audit logs record the system action
- The analyst can later confirm fraud, mark false positive, reverse, or close

This follows the operational reality that fraud can move faster than analyst queues.

### Analyst Review and Reversal Workflow

Cases can move through review states such as:

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

The reversal workflow matters because fraud systems must be fair. If a restriction is later found to be legitimate customer behavior, the analyst can reverse the decision and preserve the reason in the audit trail.

### Audit Trail and History

Boujuron records major system and analyst actions, including:

- `CASE_CREATED`
- `TRANSACTION_HELD`
- `TRANSACTION_BLOCKED`
- `AUTO_PND_APPLIED`
- `CASE_REVIEWED`
- `CONFIRMED_FRAUD`
- `MARKED_FALSE_POSITIVE`
- `REVERSED`
- `CLOSED`

Low-risk activity is not shown in the main fraud dashboard queue. It is preserved in history so the analyst dashboard stays focused on suspicious activity.

---

## Fraud Operations Dashboard

The React dashboard is the main fraud operations command center.

It includes:

- Actionable fraud decision queue
- Risk score movement
- Risk mix distribution
- Live activity feed
- Notification bell
- Operational KPI cards
- Inline analyst actions
- Investigation drawer
- User risk profiles
- Case management
- Executive analytics
- CSV export
- PDF fraud reports
- Fraud heat map
- History page
- Dark/light mode
- Mobile-responsive layout

### Investigation Drawer

The investigation drawer gives analysts the full story behind a decision:

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
- Case and audit context

### Fraud Playbooks

Boujuron recommends investigation steps for common fraud scenarios:

- Account takeover
- Bot attack
- Suspicious inflow
- Repetitive outflow
- Manipulated device
- General fraud review

### User Risk Profiles

Customer profiles can show:

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

---

## Behavioral Intelligence

Boujuron maintains organization-scoped behavioral baselines such as:

- Average transaction amount
- Trusted device fingerprints
- Trusted location history
- Normal activity-hour distribution
- Login and transaction velocity windows
- Event frequency
- Historical risk movement

Low-risk events can strengthen a customer profile. High-risk activity does not automatically become normal behavior.

---

## Authentication and Access Control

Boujuron includes controlled access features:

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

## System Architecture

Current production-oriented architecture:

```text
Client Platform / Dashboard / Partner System
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
      PostgreSQL-compatible Database
              |
              v
  React Fraud Operations Dashboard
```

Local distributed architecture also supports event-streaming mode:

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
| Risk Engine | Python rule modules, decision logic, behavioral scoring |
| Database | PostgreSQL / Supabase-compatible Postgres |
| Streaming | Kafka / Redpanda for local distributed mode |
| Authentication | JWT, invite tokens, role-based access |
| Reports | CSV and PDF exports |
| Deployment | Docker, Fly.io |
| Local Dev | Docker Compose |
| Testing | Pytest, TypeScript production build |

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
| `GET` | `/fraud-alerts` | Fetch actionable dashboard alerts |
| `GET` | `/events` | Fetch event history |
| `GET` | `/cases` | Fetch fraud cases |
| `GET` | `/cases/{case_id}` | Fetch case detail |
| `POST` | `/cases/{case_id}/review` | Mark case under review |
| `POST` | `/cases/{case_id}/confirm-fraud` | Confirm fraud |
| `POST` | `/cases/{case_id}/false-positive` | Mark false positive |
| `POST` | `/cases/{case_id}/reverse` | Reverse a restriction |
| `POST` | `/cases/{case_id}/close` | Close case |
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

Boujuron is deployable as a Dockerized FastAPI + React application.

Production deployment target:

```text
Fly.io
```

Current Fly configuration:

```text
App: boujuron-intelligence
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

## Hackathon Build Notes: How Codex & GPT-5.6 Were Used

Boujuron was built collaboratively by the Boujuron team with assistance from **Codex** and **GPT-5.6** as AI engineering and product acceleration tools.

Codex and GPT-5.6 were used to support:

- Product planning and feature prioritization for fraud operations workflows
- Translating fraud feedback into implementable technical requirements
- Drafting and refining backend API designs
- Structuring the risk decision model for debit, credit, ATO, bot, and device signals
- Improving frontend dashboard UX, mobile responsiveness, investigation drawer layout, and analyst workflow clarity
- Generating documentation drafts, architecture explanations, demo scripts, and investor/client positioning material
- Debugging deployment issues across Docker, Netlify, Render, Fly.io, Supabase/PostgreSQL, and environment variables
- Reviewing implementation direction and helping keep the product focused on solving analyst workload and fraud response problems

The implementation remained a collaborative engineering effort. The team made the product decisions, validated the fraud workflows, tested the platform, and shaped Boujuron around real fraud operations feedback.

---

## Devpost / Hackathon Access Note

If this repository is private during judging, access should be shared with:

```text
testing@devpost.com
build-week-event@openai.com
```

This ensures reviewers can inspect the implementation, documentation, and project history.

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
- Low-risk noise kept out of the dashboard queue
- Account-level PND/block only for high-confidence critical events
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
