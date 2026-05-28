CREATE TABLE IF NOT EXISTS fraud_alerts (
    id SERIAL PRIMARY KEY,
    user_id TEXT,
    reason TEXT,
    risk_score INTEGER,
    risk_level TEXT,
    timestamp TIMESTAMP
);