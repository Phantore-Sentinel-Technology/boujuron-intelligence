# Boujuron Banking Fraud Protection FRD

## Functional Modules

- Event ingestion for login, wallet, debit, credit, device, and transaction events.
- Risk scoring engine with separate debit, credit, and shared fraud rules.
- Confidence scoring separate from risk severity.
- Case management for high-risk and critical events.
- Reversal workflow for held or blocked transactions later confirmed as legitimate.
- Audit logging for major decisions and analyst actions.
- Dashboard views for fraud decisions, case status, analyst actions, and operational KPIs.

## Event Ingestion

The system accepts events through the risk API. Events include user ID, transaction ID, amount, direction, event type, device, IP, location, network, timestamp, and metadata.

Supported transaction directions:

- `DEBIT`: money leaving the customer account.
- `CREDIT`: money entering the customer account.

## Risk Scoring

The engine returns:

```json
{
  "transaction_id": "txn_123",
  "user_id": "customer_102",
  "transaction_direction": "DEBIT",
  "risk_score": 75,
  "risk_level": "HIGH",
  "confidence": "79%",
  "recommended_action": "HOLD_FOR_REVIEW",
  "reasons": ["Very large debit", "New beneficiary before debit"],
  "timestamp": "2026-06-29T12:00:00Z"
}
```

## Debit Rules

Debit rules evaluate:

- Unusual transaction amount.
- New or suspicious device.
- Blacklisted IP.
- Unusual time.
- Multiple failed login attempts.
- Sensitive account activity.
- New beneficiary or destination.
- High transaction velocity.
- Repeated failed payment attempts.
- Sudden behavior change from the user profile.

## Credit Rules

Credit rules evaluate:

- Unusual incoming amount.
- Multiple rapid credits from different sources.
- Credits followed quickly by suspicious debits.
- Suspicious sender patterns.
- Mule account behavior.
- Dormant account suddenly receiving large credits.
- Unusual credit frequency.
- High-risk credit channels.
- Reversal and chargeback risk indicators.

## Shared Rules

Shared rules evaluate device integrity, VPN/TOR/proxy usage, high-risk locations, blacklisted IPs, account takeover signals, bot behavior, mule indicators, velocity, and unusual hours.

## Decision Model

- `LOW`: normal behavior, action `ALLOW`.
- `MEDIUM`: some suspicious indicators, action `STEP_UP_VERIFY`.
- `HIGH`: strong suspicious indicators, action `HOLD_FOR_REVIEW`.
- `CRITICAL`: very strong fraud confidence, action `PND_OR_BLOCK`.

PND or hard block should be used only when confidence is extremely high.

## Confidence Scoring

Confidence increases when multiple strong signals are present, behavior differs strongly from history, known bad IP/device appears, velocity is abnormal, and credit/debit sequences are suspicious.

Confidence decreases when only one weak signal is present, historical data is limited, or the signal could be normal customer behavior.

## Case Management

Cases are created when:

- `risk_level` is `HIGH` or `CRITICAL`.
- `recommended_action` is `HOLD_FOR_REVIEW` or `PND_OR_BLOCK`.

Case statuses:

- `OPEN`
- `UNDER_REVIEW`
- `CONFIRMED_FRAUD`
- `FALSE_POSITIVE`
- `REVERSED`
- `CLOSED`

## Reversal Workflow

Endpoint:

```http
POST /cases/{case_id}/reverse
```

Expected behavior:

- Mark case as `REVERSED`.
- Store analyst note.
- Store reversal timestamp.
- Return confirmation response.
- Add audit log entry.

## Audit Logging

Audit logs record:

- `CASE_CREATED`
- `TRANSACTION_HELD`
- `TRANSACTION_BLOCKED`
- `CASE_REVIEWED`
- `MARKED_FALSE_POSITIVE`
- `CONFIRMED_FRAUD`
- `REVERSED`
- `CLOSED`

## API Endpoints

- `GET /fraud-alerts`
- `GET /events`
- `GET /cases`
- `GET /cases/{case_id}`
- `POST /cases/{case_id}/review`
- `POST /cases/{case_id}/confirm-fraud`
- `POST /cases/{case_id}/false-positive`
- `POST /cases/{case_id}/reverse`
- `POST /cases/{case_id}/close`
- `GET /audit-logs`
- `GET /users/{user_id}/activity`

## Database Tables

- `events`: stores event and transaction inputs.
- `fraud_alerts`: stores alert-level risk results.
- `cases`: stores review workflows for high-risk and critical decisions.
- `fraud_audit_logs`: stores audit evidence for system and analyst actions.

## Dashboard Requirements

The dashboard should show total cases, open cases, critical cases, high-risk cases, false positives, reversed transactions, transaction direction, transaction ID, recommended action, case status, and analyst actions.
