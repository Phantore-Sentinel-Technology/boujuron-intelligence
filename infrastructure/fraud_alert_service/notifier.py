import requests
import os

SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL")


def send_alert(alert):

    # Safe handling of reasons
    reasons = alert.get("reasons", [])

    if isinstance(reasons, list):
        reasons_text = ", ".join(reasons)
    else:
        reasons_text = str(reasons)

    message = {
        "text": f"""
🚨 *Fraud Alert Detected*

👤 User: {alert.get('user_id', 'unknown')}

⚠️ Risk Level: {alert.get('risk_level', 'UNKNOWN')}

📊 Risk Score: {alert.get('risk_score', 0)}

📝 Reason: {reasons_text}

🕒 Timestamp: {alert.get('timestamp', 'N/A')}
"""
    }

    if SLACK_WEBHOOK:
        try:
            response = requests.post(
                SLACK_WEBHOOK,
                json=message,
                timeout=5
            )

            if response.status_code == 200:
                print("✅ Alert sent to Slack")
            else:
                print("❌ Slack response:", response.text)

        except Exception as e:
            print("❌ Slack error:", e)

    else:
        print("⚠️ No Slack webhook configured")