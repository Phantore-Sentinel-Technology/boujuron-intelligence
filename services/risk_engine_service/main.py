from fastapi import FastAPI
from infrastructure.risk_engine.engine import process_event
from services.risk_engine_service.schemas import EventRequest, RiskResponse

app = FastAPI(title="Boujuron Risk Engine API")


@app.get("/")
def health():
    return {"status": "Risk Engine Running 🚀"}


@app.post("/risk-score", response_model=RiskResponse)
def calculate_risk(event: EventRequest):
    """
    Input → event
    Output → risk score + explanation
    """

    result = process_event(event.dict())

    return result