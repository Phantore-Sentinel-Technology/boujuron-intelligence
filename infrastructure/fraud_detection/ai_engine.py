from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime
from math import exp
from statistics import mean, pstdev

from .scoring import calculate_risk_score, get_risk_level, get_risk_reasons

try:
    from sklearn.ensemble import IsolationForest
except Exception:
    IsolationForest = None


VELOCITY_WINDOW_SECONDS = 60
RISK_DECAY_HALF_LIFE_HOURS = 24
MIN_HISTORY_FOR_ANOMALY = 3
MIN_ML_SAMPLES = 20


@dataclass
class UserProfile:
    devices: set = field(default_factory=set)
    ips: set = field(default_factory=set)
    locations: set = field(default_factory=set)
    event_times: deque = field(default_factory=lambda: deque(maxlen=200))
    amounts: deque = field(default_factory=lambda: deque(maxlen=100))
    hours: deque = field(default_factory=lambda: deque(maxlen=100))
    fingerprints: defaultdict = field(default_factory=lambda: defaultdict(int))
    risk_memory: float = 0.0
    last_seen: datetime | None = None


user_profiles = defaultdict(UserProfile)
feature_history = deque(maxlen=1000)
ml_model = None


def _parse_timestamp(timestamp):
    if not timestamp:
        return datetime.utcnow()

    try:
        return datetime.fromisoformat(timestamp)
    except ValueError:
        return datetime.utcnow()


def _decay(value, previous_time, current_time):
    if not previous_time:
        return 0.0

    elapsed_hours = max((current_time - previous_time).total_seconds() / 3600, 0)
    decay_factor = 0.5 ** (elapsed_hours / RISK_DECAY_HALF_LIFE_HOURS)
    return value * decay_factor


def _event_fingerprint(event):
    return "|".join([
        event.get("device_type", "unknown").lower().strip(),
        event.get("ip", "0.0.0.0").strip(),
        event.get("location", "unknown").lower().strip(),
        event.get("event_type", "unknown").lower().strip(),
    ])


def _velocity_score(profile, event_time):
    recent_events = [
        t for t in profile.event_times
        if (event_time - t).total_seconds() <= VELOCITY_WINDOW_SECONDS
    ]
    events_per_minute = len(recent_events) + 1
    score = min(events_per_minute * 10, 50)

    if events_per_minute >= 20:
        return score, ["Extreme event velocity"], events_per_minute
    if events_per_minute >= 10:
        return score, ["High event velocity"], events_per_minute
    if events_per_minute >= 5:
        return score, ["Elevated event velocity"], events_per_minute

    return 0, [], events_per_minute


def _anomaly_score(profile, event, event_time):
    if len(profile.event_times) < MIN_HISTORY_FOR_ANOMALY:
        return 0, []

    score = 0
    reasons = []

    device = event.get("device_type", "unknown")
    ip = event.get("ip", "0.0.0.0")
    location = event.get("location", "unknown")
    amount = float(event.get("amount", 0) or 0)

    if device not in profile.devices:
        score += 20
        reasons.append("User anomaly: new device")

    if ip not in profile.ips:
        score += 15
        reasons.append("User anomaly: new IP")

    if location not in {"unknown", ""} and profile.locations and location not in profile.locations:
        score += 15
        reasons.append("User anomaly: new location")

    if len(profile.amounts) >= MIN_HISTORY_FOR_ANOMALY:
        avg_amount = mean(profile.amounts)
        amount_std = pstdev(profile.amounts) or 1
        if amount > avg_amount + (3 * amount_std) and amount > 0:
            score += 25
            reasons.append("User anomaly: unusual amount")

    if len(profile.hours) >= MIN_HISTORY_FOR_ANOMALY:
        avg_hour = mean(profile.hours)
        hour_distance = min(abs(event_time.hour - avg_hour), 24 - abs(event_time.hour - avg_hour))
        if hour_distance >= 6:
            score += 15
            reasons.append("User anomaly: unusual active hour")

    return min(score, 60), reasons


def _fingerprint_score(profile, event):
    if len(profile.event_times) < MIN_HISTORY_FOR_ANOMALY:
        return 0, []

    fingerprint = _event_fingerprint(event)
    if profile.fingerprints[fingerprint] == 0:
        return 20, ["Behavioral fingerprint mismatch"]

    return 0, []


def _build_features(event, profile, rule_score, events_per_minute):
    return [
        float(event.get("amount", 0) or 0),
        float(_parse_timestamp(event.get("timestamp")).hour),
        float(events_per_minute),
        float(len(profile.devices)),
        float(len(profile.ips)),
        float(len(profile.locations)),
        float(rule_score),
    ]


def _ml_score(features):
    global ml_model

    if IsolationForest is None:
        return 0, [], "unavailable"

    if len(feature_history) < MIN_ML_SAMPLES:
        return 0, [], "warming_up"

    try:
        ml_model = IsolationForest(
            n_estimators=100,
            contamination=0.08,
            random_state=42,
        )
        ml_model.fit(list(feature_history))

        prediction = ml_model.predict([features])[0]
        raw_score = float(ml_model.decision_function([features])[0])

        if prediction == -1:
            confidence = min(35, max(15, int(abs(raw_score) * 100)))
            return confidence, ["ML anomaly detected"], "anomaly"

        return 0, [], "normal"
    except Exception:
        return 0, [], "error"


def _update_profile(profile, event, event_time, final_score, features):
    decayed_memory = _decay(profile.risk_memory, profile.last_seen, event_time)

    profile.devices.add(event.get("device_type", "unknown"))
    profile.ips.add(event.get("ip", "0.0.0.0"))

    location = event.get("location", "unknown")
    if location not in {"", "unknown"}:
        profile.locations.add(location)

    profile.event_times.append(event_time)
    profile.amounts.append(float(event.get("amount", 0) or 0))
    profile.hours.append(event_time.hour)
    profile.fingerprints[_event_fingerprint(event)] += 1
    profile.risk_memory = max(decayed_memory, final_score)
    profile.last_seen = event_time
    feature_history.append(features)


def analyze_event(event):
    user_id = event.get("user_id", "unknown_user")
    event_time = _parse_timestamp(event.get("timestamp"))
    profile = user_profiles[user_id]

    rule_score = calculate_risk_score(event, reason="multi-factor analysis")
    rule_reasons = get_risk_reasons(event)

    velocity_score, velocity_reasons, events_per_minute = _velocity_score(profile, event_time)
    anomaly_score, anomaly_reasons = _anomaly_score(profile, event, event_time)
    fingerprint_score, fingerprint_reasons = _fingerprint_score(profile, event)

    decayed_memory = _decay(profile.risk_memory, profile.last_seen, event_time)
    risk_decay_score = min(int(decayed_memory * 0.25), 20)

    features = _build_features(event, profile, rule_score, events_per_minute)
    ml_score, ml_reasons, ml_status = _ml_score(features)

    score = min(
        rule_score
        + velocity_score
        + anomaly_score
        + fingerprint_score
        + risk_decay_score
        + ml_score,
        100,
    )

    reasons = []
    for reason in (
        rule_reasons
        + velocity_reasons
        + anomaly_reasons
        + fingerprint_reasons
        + ml_reasons
    ):
        if reason != "Normal behavior" and reason not in reasons:
            reasons.append(reason)

    if risk_decay_score:
        reasons.append("Residual risk from recent activity")

    if not reasons:
        reasons = ["Normal behavior"]

    _update_profile(profile, event, event_time, score, features)

    return {
        "user_id": user_id,
        "risk_score": score,
        "risk_level": get_risk_level(score),
        "reasons": reasons,
        "timestamp": event.get("timestamp"),
        "intelligence": {
            "rule_score": rule_score,
            "anomaly_score": anomaly_score,
            "velocity_score": velocity_score,
            "events_per_minute": events_per_minute,
            "fingerprint_score": fingerprint_score,
            "risk_decay_score": risk_decay_score,
            "ml_score": ml_score,
            "ml_status": ml_status,
            "profile": {
                "known_devices": len(profile.devices),
                "known_ips": len(profile.ips),
                "known_locations": len(profile.locations),
                "history_events": len(profile.event_times),
            },
        },
    }
