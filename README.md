# Boujuron Intelligence

**Boujuron Intelligence** is a **Behavioral Risk Intelligence Platform** designed to help fintech companies, SaaS platforms, marketplaces, and API-driven services detect abnormal user behavior and potential fraud in real time.

The platform processes user behavioral events, extracts meaningful signals, and applies anomaly detection models to identify suspicious activity before it becomes a security threat.

Phantore Sentinel is built with a **scalable, event-driven architecture** that supports high-volume real-time analytics and multi-tenant SaaS deployments.

---

# Vision

Modern digital platforms face increasing threats such as:

* Account takeovers
* Fraudulent transactions
* Bot activity
* Credential stuffing
* Suspicious behavioral patterns

Phantore Sentinel provides **behavioral intelligence APIs** that enable platforms to detect abnormal activity early using **real-time event processing and machine learning**.

---

# System Architecture

The system is built using a **distributed event streaming architecture**.

```
Client Platforms
(Fintech | SaaS | Marketplaces | APIs)
            │
            ▼
      API Gateway
(Authentication / Rate Limiting)
            │
            ▼
   Event Ingestion Service
        (FastAPI)
            │
            ▼
      Kafka Event Stream
            │
            ▼
     Stream Processing
     (Kafka Consumers)
            │
            ▼
     Feature Extraction
  Behavioral Signal Engine
            │
            ▼
        Feature Store
   (Redis + PostgreSQL)
            │
            ▼
   ML Anomaly Detection
 (Isolation Forest / Clustering)
            │
            ▼
     Risk Scoring Engine
            │
            ▼
   Risk Intelligence Database
        (PostgreSQL)
            │
            ▼
   Monitoring Dashboard
```

---

# Core Platform Components

### API Gateway

Handles request routing, authentication, and rate limiting for client integrations.

### Event Ingestion Service

Receives behavioral activity events from client platforms via REST API.

### Kafka Event Streaming

Provides a scalable event backbone for real-time event processing.

### Stream Processing Workers

Kafka consumers process incoming events and trigger feature extraction pipelines.

### Feature Extraction Engine

Transforms raw user activity into behavioral signals used by anomaly detection models.

### Feature Store

Stores behavioral features used for machine learning inference.

### Anomaly Detection Engine

Uses unsupervised learning models to identify abnormal behavior patterns.

### Risk Scoring Engine

Combines anomaly scores and behavioral signals into a final risk score.

### Risk Intelligence Database

Stores events, anomaly scores, alerts, and user risk profiles.

### Monitoring & Alerting

Provides dashboards and APIs for monitoring suspicious activity.

---

# Technology Stack

| Layer             | Technology               |
| ----------------- | ------------------------ |
| API Gateway       | NGINX / Cloud Gateway    |
| Backend Services  | Python + FastAPI         |
| Event Streaming   | Apache Kafka             |
| Stream Processing | Kafka Consumers (Python) |
| Machine Learning  | Scikit-learn / PyTorch   |
| Feature Store     | Redis + PostgreSQL       |
| Primary Database  | PostgreSQL               |
| Caching           | Redis                    |
| Containerization  | Docker                   |
| Orchestration     | Kubernetes (future)      |
| Infrastructure    | Cloud (AWS / GCP / VPS)  |

---

# Event Processing Flow

1. Client sends behavioral event to API Gateway
2. Event is forwarded to Event Ingestion Service
3. Event is published to Kafka topic
4. Stream processing workers consume the event
5. Behavioral features are extracted
6. ML models calculate anomaly scores
7. Risk scoring engine generates risk levels
8. Risk data is stored in PostgreSQL
9. Clients retrieve alerts and analytics via API or dashboard

---

# Example Event Payload

```json
{
  "user_id": "123",
  "event_type": "login",
  "device": "mobile",
  "ip": "192.168.1.1",
  "timestamp": "2026-03-13T10:30:00Z"
}
```

---

# Project Structure

```
phantore-sentinel
│
├── services
│   ├── event-ingestion-service
│   ├── stream-processors
│   └── risk-engine
│
├── infrastructure
│   ├── kafka
│   ├── database
│   └── docker
│
├── docs
│   └── architecture
│
├── scripts
│
├── README.md
└── docker-compose.yml
```

---

# Development Roadmap

### Phase 1 — Core Event Pipeline

* API Gateway setup
* Event Ingestion Service
* Kafka event streaming
* Basic Kafka consumer
* PostgreSQL event storage

Goal:

```
Client → API → Kafka → Consumer → Database
```

---

### Phase 2 — Behavioral Intelligence

* Feature extraction engine
* Feature store implementation
* Behavioral signal processing
* Initial anomaly detection models

---

### Phase 3 — Risk Intelligence Engine

* ML anomaly detection pipeline
* Risk scoring engine
* Alerting system

---

### Phase 4 — Monitoring Platform

* Admin dashboard
* Risk monitoring APIs
* Real-time alerts

---

# Running the Project

Prerequisites

* Docker
* Python 3.11+
* Apache Kafka
* PostgreSQL

Start infrastructure

```
docker-compose up -d
```

Run event ingestion service

```
cd services/event-ingestion-service
uvicorn main:app --reload
```

---

# Fraud Intelligence API

Admins create client API keys from **Settings → Fraud Intelligence API Keys**.
The full secret is shown only once.

```http
POST /risk-score
X-API-Key: bj_live_your_secret_key
Idempotency-Key: transaction-123
Content-Type: application/json
```

Request:

```json
{
  "user_id": "123",
  "transaction_id": "txn-123",
  "amount": 500000,
  "device": "android",
  "device_id": "device-a19",
  "ip": "102.88.45.21",
  "location": "nigeria",
  "network": "VPN",
  "event_type": "transaction",
  "timestamp": "2026-06-19T10:30:00Z",
  "is_rooted": false,
  "is_emulator": false
}
```

Response:

```json
{
  "decision_id": 42,
  "user_id": "123",
  "transaction_id": "txn-123",
  "risk_score": 80,
  "risk_level": "HIGH",
  "action": "BLOCK",
  "recommendation": "BLOCK_AND_REVIEW",
  "confidence": 84,
  "reasons": [
    "Large transaction",
    "VPN usage detected",
    "New device"
  ],
  "signals": [
    {
      "category": "TRANSACTION",
      "label": "Large transaction",
      "points": 30,
      "evidence": "Amount 500000.00 is at least 500,000"
    }
  ],
  "behavioral_match": false,
  "created_at": "2026-06-19 10:30:01"
}
```

Every request is stored as a risk decision. Medium, high, and critical decisions also create dashboard alerts and investigation cases.

## Behavioral Intelligence

Boujuron maintains organization-scoped, long-term profiles for every user:

- Incremental average transaction amount
- Trusted device fingerprints
- Trusted location history
- Normal activity-hour distribution
- Transaction and login velocity windows
- Total and trusted profile event counts

Behavioral scoring begins after the configured minimum number of trusted events. This avoids treating a new account's first activity as a mature baseline.

Admins configure each organization's policy from **Settings → Organization Baselines**, including:

- Amount spike multiplier
- New device/location weights
- Activity-hour sensitivity
- Velocity window and event limits
- Adaptive learning controls

Low-risk events can update profiles automatically. High-risk activity never becomes normal automatically. When an analyst marks a case as `FALSE_POSITIVE`, Boujuron can safely learn that reviewed event. Model health and analyst-label precision are available under **Settings → Adaptive Learning Health**.

---

# Security

The platform is designed to support:

* API authentication
* Rate limiting
* Event validation
* Secure event pipelines
* Behavioral fraud detection

---

# Founding Team

**Iniobong Udoette**
Founder & Product Lead

Responsible for product strategy, market development, and partnerships.

**Olabowale Babatunde Ipaye**
Chief Technology Officer

Responsible for system architecture, backend platform development, and infrastructure.

---

# License

This project is proprietary software and part of the Phantore Sentinel platform.

---

# Future Vision

Phantore Sentinel aims to become a **behavioral risk intelligence layer for modern digital platforms**, helping companies detect fraud and abnormal activity using **machine learning and real-time analytics**.

---
