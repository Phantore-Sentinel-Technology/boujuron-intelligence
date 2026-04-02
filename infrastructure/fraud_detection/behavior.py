from collections import defaultdict

# user profile storage (in memory for now)
user_profiles = defaultdict(lambda: {
    "ips": set,
    "device": set,
    "event_count": 0
})


def update_profile(event):
    profile = user_profiles[event["user_id"]]

    profile["ips"].add(event["ip"])
    profile["devices"].add(event["device_type"])
    profile["event_count"] += 1

    return profile


def get_profile(user_id):
    return user_profiles[user_id]
