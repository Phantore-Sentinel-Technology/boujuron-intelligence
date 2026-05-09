from .models import Event
from .kafka_producer import send_event
from fastapi import FastAPI


app = FastAPI()


@app.get("/")
def health():
    return {"status": "Boujuron API is up and running!"}


@app.post("/events")
def ingest_event(event: Event):
    send_event(event.dict())

    return {
        "message": "Event ingested successfully",
        "event": event
    }
