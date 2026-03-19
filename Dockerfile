FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH=/app

# ✅ Improve pip reliability
RUN pip install --upgrade pip

COPY requirements.txt .

RUN pip install --no-cache-dir --default-timeout=100 -r requirements.txt

COPY . .

CMD ["uvicorn", "services.event_ingestion_service.main:app", "--host", "0.0.0.0", "--port", "8000"]