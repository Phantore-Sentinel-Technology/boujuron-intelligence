from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

UserRole = str


class AuthRegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: UserRole = "Fraud Analyst"
    invite_token: str


class AuthLoginRequest(BaseModel):
    email: str
    password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ForgotPasswordResponse(BaseModel):
    message: str
    reset_token: str | None = None
    reset_url: str | None = None


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class AuthUserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: UserRole
    organization_id: int | None = None


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserResponse


class OrganizationCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    admin_email: str


class OrganizationResponse(BaseModel):
    id: int
    name: str
    slug: str
    admin_invite_url: str | None = None
    created_at: str


class InviteCreateRequest(BaseModel):
    email: str
    role: UserRole = "Read-Only Auditor"
    expires_in_hours: int = 24


class InviteResponse(BaseModel):
    id: int
    token: str
    invite_url: str
    email: str
    role: UserRole
    expires_at: str
    used_at: str | None = None
    created_by: str | None = None
    created_at: str


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    key_prefix: str
    api_key: str | None = None
    active: bool
    request_count: int = 0
    last_used_at: str | None = None
    created_at: str


class ApiKeyUsageResponse(BaseModel):
    total_requests: int
    requests_this_month: int
    blocked: int
    challenged: int
    allowed: int


class InvoiceResponse(BaseModel):
    id: int
    invoice_number: str
    period: str
    amount: float
    currency: str
    status: str
    created_at: str


class AlertDestinationRequest(BaseModel):
    name: str
    channel: str
    target: str
    minimum_risk: str = "HIGH"
    enabled: bool = True

    @field_validator("channel")
    @classmethod
    def validate_channel(cls, value):
        normalized = value.upper()
        if normalized not in {"SLACK", "TEAMS", "EMAIL", "WEBHOOK"}:
            raise ValueError("channel must be SLACK, TEAMS, EMAIL, or WEBHOOK")
        return normalized


class AlertDestinationResponse(AlertDestinationRequest):
    id: int
    last_status: str | None = None
    last_sent_at: str | None = None
    created_at: str


class EvidenceNode(BaseModel):
    id: str
    type: str
    label: str
    risk: str
    count: int = 1


class EvidenceEdge(BaseModel):
    source: str
    target: str
    relationship: str
    count: int = 1


class EvidenceGraphResponse(BaseModel):
    nodes: list[EvidenceNode]
    edges: list[EvidenceEdge]
    suspected_ring: bool


class ConsortiumSettingsResponse(BaseModel):
    enabled: bool
    share_devices: bool
    share_ips: bool
    share_emails: bool
    share_phones: bool


class ConsortiumSettingsUpdate(BaseModel):
    enabled: bool
    share_devices: bool = True
    share_ips: bool = True
    share_emails: bool = False
    share_phones: bool = False


class BehaviorSettingsResponse(BaseModel):
    organization_id: int
    organization_name: str
    amount_spike_multiplier: float
    minimum_amount_delta: float
    new_device_points: int
    new_location_points: int
    unusual_hour_points: int
    velocity_window_minutes: int
    transaction_velocity_limit: int
    login_velocity_limit: int
    velocity_points: int
    minimum_profile_events: int
    adaptive_learning_enabled: bool
    trusted_learning_max_score: int


class BehaviorSettingsUpdate(BaseModel):
    amount_spike_multiplier: float | None = Field(default=None, ge=1.5, le=50)
    minimum_amount_delta: float | None = Field(default=None, ge=0)
    new_device_points: int | None = Field(default=None, ge=0, le=100)
    new_location_points: int | None = Field(default=None, ge=0, le=100)
    unusual_hour_points: int | None = Field(default=None, ge=0, le=100)
    velocity_window_minutes: int | None = Field(default=None, ge=1, le=1440)
    transaction_velocity_limit: int | None = Field(default=None, ge=1, le=10000)
    login_velocity_limit: int | None = Field(default=None, ge=1, le=10000)
    velocity_points: int | None = Field(default=None, ge=0, le=100)
    minimum_profile_events: int | None = Field(default=None, ge=1, le=1000)
    adaptive_learning_enabled: bool | None = None
    trusted_learning_max_score: int | None = Field(default=None, ge=0, le=100)


class BehaviorEvaluationResponse(BaseModel):
    labeled_decisions: int
    confirmed_fraud: int
    false_positives: int
    needs_review: int
    precision: float
    false_positive_rate: float
    profiles_learning: int
    trusted_events_learned: int


class RiskScoreRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=160)
    amount: float = Field(default=0, ge=0)
    transaction_direction: str = "DEBIT"
    device: str | None = None
    device_type: str | None = None
    device_id: str | None = None
    platform: str | None = None
    operating_system: str | None = None
    browser: str | None = None
    user_agent: str | None = None
    screen_resolution: str | None = None
    timezone: str | None = None
    language: str | None = None
    app_version: str | None = None
    device_attestation: str | None = None
    ip: str = Field(min_length=1, max_length=160)
    location: str = ""
    network: str = ""
    event_type: str = "transaction"
    transaction_id: str | None = None
    timestamp: str | None = None
    is_rooted: bool = False
    is_emulator: bool = False
    browser_tampering: bool = False
    sim_swap_detected: bool = False
    password_changed_recently: bool = False
    new_beneficiary_added: bool = False
    mule_account_suspected: bool = False
    failed_login_count: int = Field(default=0, ge=0)
    accounts_from_ip: int = Field(default=0, ge=0)
    accounts_from_device: int = Field(default=0, ge=0)
    registration_count: int = Field(default=0, ge=0)
    automation_score: int = Field(default=0, ge=0, le=100)
    repeated_failed_payments: bool = False
    rapid_credit_count: int = Field(default=0, ge=0)
    different_sender_count: int = Field(default=0, ge=0)
    debits_after_credit_count: int = Field(default=0, ge=0)
    dormant_days: int = Field(default=0, ge=0)
    credit_frequency_count: int = Field(default=0, ge=0)
    suspicious_sender: bool = False
    chargeback_risk: bool = False
    channel: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp(cls, value):
        if value:
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("timestamp must be ISO 8601") from exc
        return value

    @field_validator("transaction_direction")
    @classmethod
    def validate_transaction_direction(cls, value):
        normalized = value.upper().strip()
        if normalized not in {"DEBIT", "CREDIT"}:
            raise ValueError("transaction_direction must be DEBIT or CREDIT")
        return normalized


class RiskSignalResponse(BaseModel):
    category: str
    label: str
    points: int
    evidence: str


class RuleCondition(BaseModel):
    field: str
    operator: str
    value: Any

    @field_validator("field")
    @classmethod
    def validate_field(cls, value):
        allowed = {
            "amount", "risk_score", "risk_level", "event_type", "location", "network",
            "device_type", "is_new_device", "is_rooted", "is_emulator",
            "browser_tampering", "sim_swap_detected", "failed_login_count",
        }
        if value not in allowed:
            raise ValueError(f"field must be one of: {', '.join(sorted(allowed))}")
        return value

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, value):
        normalized = value.upper()
        allowed = {"EQ", "NEQ", "GT", "GTE", "LT", "LTE", "IN", "CONTAINS"}
        if normalized not in allowed:
            raise ValueError(f"operator must be one of: {', '.join(sorted(allowed))}")
        return normalized


class DecisionRuleRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    conditions: list[RuleCondition] = Field(min_length=1, max_length=10)
    action: str
    score_adjustment: int = Field(default=0, ge=0, le=100)
    priority: int = Field(default=100, ge=1, le=10000)
    enabled: bool = True

    @field_validator("action")
    @classmethod
    def validate_action(cls, value):
        normalized = value.upper()
        if normalized not in {"ALLOW", "CHALLENGE", "BLOCK"}:
            raise ValueError("action must be ALLOW, CHALLENGE, or BLOCK")
        return normalized


class DecisionRuleResponse(DecisionRuleRequest):
    id: int
    organization_id: int
    created_by: str | None = None
    created_at: str
    updated_at: str


class DeviceIntelligenceResponse(BaseModel):
    fingerprint: str
    status: str
    trust_score: int
    is_new_device: bool
    first_seen_at: str
    last_seen_at: str
    event_count: int
    integrity_flags: list[str]


class AccountTakeoverResponse(BaseModel):
    detected: bool
    score: int
    level: str
    recommendation: str
    indicators: list[str]


class RiskScoreResponse(BaseModel):
    decision_id: int
    user_id: str
    transaction_id: str
    transaction_direction: str | None = None
    risk_score: int
    risk_level: str
    action: str
    recommendation: str
    confidence: float
    reasons: list[str]
    signals: list[RiskSignalResponse]
    behavioral_match: bool
    device_intelligence: DeviceIntelligenceResponse | None = None
    account_takeover: AccountTakeoverResponse | None = None
    action_decision_id: int | None = None
    matched_rules: list[str] = Field(default_factory=list)
    created_at: str


class EventResponse(BaseModel):
    user_id: str
    event_type: str
    device_type: str
    ip: str
    timestamp: str


class FraudAlertResponse(BaseModel):
    id: int | None = None
    case_id: int | None = None
    case_number: str | None = None
    case_status: str | None = None
    analyst_feedback: str | None = None
    closure_note: str | None = None
    transaction_id: str | None = None
    transaction_direction: str | None = None
    user_id: str
    reason: str
    timestamp: str
    risk_score: str
    risk_level: str
    recommended_action: str | None = None
    confidence: float | None = None
    signals_triggered: int | None = None
    behavioral_match: bool | None = None


class DemoFraudEventRequest(BaseModel):
    user_id: str = "acct_501"
    transaction_direction: str = "DEBIT"
    event_type: str = "large_transfer"
    device_type: str = "rooted device"
    ip: str = "45.90.12.10"
    timestamp: str | None = None
    amount: float = 2500000
    location: str = "russia"
    network: str = "TOR"

    @field_validator("transaction_direction")
    @classmethod
    def validate_transaction_direction(cls, value):
        normalized = value.upper().strip()
        if normalized not in {"DEBIT", "CREDIT"}:
            raise ValueError("transaction_direction must be DEBIT or CREDIT")
        return normalized


class ScoreBreakdownItem(BaseModel):
    label: str
    points: int
    evidence: str


class UserProfileEvent(BaseModel):
    event_type: str
    device_type: str
    ip: str
    location: str | None = None
    network: str | None = None
    amount: float | None = None
    timestamp: str


class RiskTimelinePoint(BaseModel):
    timestamp: str
    score: int
    level: str
    reason: str


class BehaviorAnomaly(BaseModel):
    label: str
    severity: str
    detail: str


class DeviceProfileResponse(BaseModel):
    fingerprint: str
    label: str
    status: str
    trust_score: int
    first_seen_at: str
    last_seen_at: str
    event_count: int
    last_ip: str | None = None
    last_location: str | None = None
    integrity_flags: list[str]


class DeviceTrustUpdate(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, value):
        normalized = value.upper()
        if normalized not in {"NEW", "TRUSTED", "SUSPICIOUS", "BLOCKED"}:
            raise ValueError("status must be NEW, TRUSTED, SUSPICIOUS, or BLOCKED")
        return normalized


class AccountSecurityResponse(BaseModel):
    takeover_risk: int
    takeover_level: str
    recommendation: str
    recent_failed_logins: int
    password_changed_at: str | None = None
    sim_changed_at: str | None = None
    last_successful_login_at: str | None = None
    last_login_location: str | None = None
    last_login_ip: str | None = None
    last_login_device: str | None = None
    indicators: list[str]


class UserProfileResponse(BaseModel):
    user_id: str
    current_risk: int
    risk_level: str
    risk_trend: str
    known_devices: list[str]
    new_devices: list[str]
    known_locations: list[str]
    current_location: str | None = None
    ip_history: list[str]
    behavioral_profile: dict[str, str]
    behavior_anomalies: list[BehaviorAnomaly]
    risk_timeline: list[RiskTimelinePoint]
    recent_events: list[UserProfileEvent]
    previous_investigations: list[FraudAlertResponse]
    score_breakdown: list[ScoreBreakdownItem]
    device_inventory: list[DeviceProfileResponse] = Field(default_factory=list)
    account_security: AccountSecurityResponse | None = None


CaseStatus = str
CasePriority = str
AnalystFeedback = str


class CaseSummaryResponse(BaseModel):
    id: int
    case_number: str
    user_id: str
    transaction_id: str | None = None
    transaction_direction: str | None = None
    risk_score: int
    risk_level: str
    confidence: float | None = None
    recommended_action: str | None = None
    status: CaseStatus
    priority: CasePriority
    assigned_to: str | None = None
    analyst_feedback: AnalystFeedback | None = None
    created_at: str
    updated_at: str


class CaseNoteResponse(BaseModel):
    id: int
    author: str
    note: str
    created_at: str


class CaseTimelineResponse(BaseModel):
    id: int
    event_type: str
    description: str
    actor: str
    created_at: str


class CaseDetailResponse(CaseSummaryResponse):
    reason: str
    recommended_action: str | None = None
    decision: str | None = None
    potential_loss: float | None = None
    actual_loss: float | None = None
    fraud_signals: list[str]
    score_breakdown: list[ScoreBreakdownItem]
    notes: list[CaseNoteResponse]
    timeline: list[CaseTimelineResponse]


class CaseUpdateRequest(BaseModel):
    assigned_to: str | None = None
    status: CaseStatus | None = None
    priority: CasePriority | None = None
    analyst_feedback: AnalystFeedback | None = None
    decision: str | None = None
    potential_loss: float | None = None
    actual_loss: float | None = None


class CaseNoteRequest(BaseModel):
    note: str


class CaseActionRequest(BaseModel):
    analyst_note: str | None = None


class CaseActionResponse(BaseModel):
    message: str
    case_id: str
    transaction_id: str | None = None
    status: str


class AuditLogResponse(BaseModel):
    id: int
    case_id: int | None = None
    transaction_id: str | None = None
    user_id: str | None = None
    action_taken: str
    previous_status: str | None = None
    new_status: str | None = None
    analyst_note: str | None = None
    created_at: str


class NotificationResponse(BaseModel):
    id: str
    title: str
    message: str
    severity: str
    case_id: int | None = None
    user_id: str | None = None
    created_at: str
    read: bool = False


class InvestigationFeedItemResponse(BaseModel):
    id: str
    event_type: str
    description: str
    actor: str
    case_id: int | None = None
    case_number: str | None = None
    user_id: str | None = None
    risk_level: str | None = None
    created_at: str


class IntelligenceActivityResponse(BaseModel):
    notifications: list[NotificationResponse]
    feed: list[InvestigationFeedItemResponse]


class AnalyticsOverviewResponse(BaseModel):
    total_events: int
    fraud_alerts: int
    confirmed_fraud_cases: int
    fraud_prevention_rate: float
    false_positive_rate: float
    average_investigation_minutes: float
    cases_resolved: int


class TrendPointResponse(BaseModel):
    label: str
    value: int


class RiskDistributionResponse(BaseModel):
    level: str
    count: int


class AnalystPerformanceResponse(BaseModel):
    analyst: str
    assigned_cases: int
    resolved_cases: int
    confirmed_fraud: int
    false_positives: int


class FraudHeatMapPointResponse(BaseModel):
    location: str
    alerts: int
    average_risk: float
    highest_risk: str
