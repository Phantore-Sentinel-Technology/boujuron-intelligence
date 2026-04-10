import sqlite3
import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib

# Connect DB
conn = sqlite3.connect("events.db")

# Load features
df = pd.read_sql_query("SELECT * FROM ml_features", conn)

if df.empty:
    print("❌ No data to train model")
    exit()

# Select features
X = df[[
    "num_devices",
    "num_ips",
    "total_requests"
]]

# Train model
model = IsolationForest(
    n_estimators=100,
    contamination=0.05,
    random_state=42
)

model.fit(X)

# Save model
joblib.dump(model, "fraud_model.pkl")

print("✅ Model trained and saved")