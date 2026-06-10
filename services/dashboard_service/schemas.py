from pydantic import BaseModel

UserRole = str


class AuthRegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    role: UserRole = "Fraud Analyst"


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


class AuthTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserResponse


class EventResponse(BaseModel):
    user_id: str
    event_type: str
    device_type: str
    ip: str
    timestamp: str


class FraudAlertResponse(BaseModel):
    user_id: str
    reason: str
    timestamp: str
    risk_score: str
    risk_level: str
    recommended_action: str | None = None
    confidence: float | None = None
    signals_triggered: int | None = None
    behavioral_match: bool | None = None


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


CaseStatus = str
CasePriority = str
AnalystFeedback = str


class CaseSummaryResponse(BaseModel):
    id: int
    case_number: str
    user_id: str
    risk_score: int
    risk_level: str
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
