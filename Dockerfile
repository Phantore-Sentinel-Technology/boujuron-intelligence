FROM node:22-alpine AS frontend-build

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm install

COPY frontend .
RUN npm run build

FROM python:3.11-slim

WORKDIR /app

COPY requirements-dashboard.txt .

RUN pip install --default-timeout=1000 --no-cache-dir -r requirements-dashboard.txt

COPY . .
COPY --from=frontend-build /frontend/dist /app/frontend/dist

ENV PYTHONPATH=/app

EXPOSE 8000

RUN addgroup --system boujuron && \
    adduser --system --ingroup boujuron boujuron && \
    chown -R boujuron:boujuron /app

USER boujuron

CMD ["sh", "-c", "uvicorn services.dashboard_service.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
