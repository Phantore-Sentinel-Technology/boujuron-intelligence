from collections import defaultdict

# In-memory behavior profiles
user_profiles = defaultdict(
    lambda: {
        "devices": set(),
        "ips": set(),
        "total_requests": 0
    }
)


def update_profile(event):
    user_id = event["user_id"]

    profile = user_profiles[user_id]

    # Track device
    profile["devices"].add(event["device_type"])

    # Track IP
    profile["ips"].add(event["ip"])

    # Track request count
    profile["total_requests"] += 1

    return {
        "known_devices": list(profile["devices"]),
        "known_ips": list(profile["ips"]),
        "total_requests": profile["total_requests"]
    }