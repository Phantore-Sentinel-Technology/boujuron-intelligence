import psycopg2
import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib

from config.settings import settings

# Connect Postgres
conn = psycopg2.connect(settings.DATABASE_URL)

# Load data
df = pd.read_sql_query("SELECT * FROM ml_features", conn)

if df.empty:
    print("❌ No data to train model")
    exit()

X = df[["num_devices", "num_ips", "total_requests"]]

model = IsolationForest(
    n_estimators=100,
    contamination=0.05,
    random_state=42
)

model.fit(X)

joblib.dump(model, "fraud_model.pkl")

print("✅ Model trained and saved")