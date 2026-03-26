import requests
import os

SLACK_WEBHOOK = os.getenv("SLACK_WEBHOOK_URL")


def send_alert(alert):
    message = {
        "text": f"""
🚨 *Fraud Alert Detected*
User: {alert['user_id']}
Risk Score: {alert['risk_score']}
Reason: {alert['reason']}
IP: {alert['event']['ip']}
Device: {alert['event']['device_type']}
"""
    }

    if SLACK_WEBHOOK:
        try:
            requests.post(SLACK_WEBHOOK, json=message)
            print("✅ Alert sent to Slack")
        except Exception as e:
            print("Slack error:", e)
    else:
        print("No slack webhook configured")
