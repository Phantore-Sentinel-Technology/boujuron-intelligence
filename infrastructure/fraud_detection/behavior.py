from collections import defaultdict

# Store user behavior profile
user_profiles = defaultdict(lambda: {
    "devices": set(),
    "ips": set(),
    "avg_requests": 0,
    "total_requests": 0
})


def update_profile(event):
    profile = user_profiles[event["user_id"]]

    profile["devices"].add(event["device_type"])
    profile["ips"].add(event["ip"])
    profile["total_requests"] += 1

    # Update avg requests (simple moving avg)
    profile["avg_requests"] = profile["total_requests"] / max(1, len(profile["devices"]))

    return profile


def get_profile(user_id):
    return user_profiles[user_id]