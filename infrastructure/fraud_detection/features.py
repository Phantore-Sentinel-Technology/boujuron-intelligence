def extract_features(event, profile):
    return {
        "user_id": event["user_id"],
        "event_type": event["event_type"],
        "device_type": event["device_type"],
        "ip": event["ip"],
        "num_devices": len(profile["devices"]),
        "num_ips": len(profile["ips"]),
        "total_requests": profile["total_requests"],
        "timestamp": event["timestamp"]
    }
