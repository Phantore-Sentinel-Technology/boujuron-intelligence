from pydantic import BaseModel


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
