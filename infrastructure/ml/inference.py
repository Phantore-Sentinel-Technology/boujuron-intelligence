import joblib
import numpy as np

# Load trained model
model = joblib.load("fraud_model.pkl")


def predict_fraud(features):
    X = np.array([[
        features["num_devices"],
        features["num_ips"],
        features["total_requests"]
    ]])

    prediction = model.predict(X)[0]  # -1 = anomaly, 1 = normal
    score = model.decision_function(X)[0]

    is_anomaly = prediction == -1

    return is_anomaly, float(score)
