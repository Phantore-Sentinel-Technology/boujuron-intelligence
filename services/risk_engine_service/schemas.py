from pydantic import BaseModel
from typing import List


class EventRequest(BaseModel):
    user_id: str
    event_type: str
    device_type: str
    ip: str
    timestamp: str


class RiskResponse(BaseModel):
    user_id: str
    risk_score: int
    risk_level: str
    reasons: List[str]
    timestamp: str