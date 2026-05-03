from collections import defaultdict
from datetime import datetime

user_profiles = defaultdict(lambda: {
    "device": set(),
    "ips": set(),
    "events": [],
    "last_seen": None
})


def update_profile(event):
    user_id = event["user_id"]

    profile = user_profiles[user_id]

    profile["devices"].add(event["device_type"])
    profile["ips"].add(event["ips"])

    profile["event"].append(event)
    profile["last_seen"] = event("timestamp")

    return profile
