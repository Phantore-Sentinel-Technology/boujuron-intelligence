from pydantic import BaseModel


class Event(BaseModel):
    user_id: str
    event_type: str
    device_type: str
    ip: str
    timestamp: str
