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
