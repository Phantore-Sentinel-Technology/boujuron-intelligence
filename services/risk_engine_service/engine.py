from services.risk_engine_service.credit_rules import credit_signals
from services.risk_engine_service.debit_rules import debit_signals
from services.risk_engine_service.shared_rules import (
    action_for_decision,
    calculate_confidence,
    level_from_score,
    shared_transaction_signals,
)


def _normalize_direction(event: dict) -> str:
    direction = str(event.get("transaction_direction") or event.get("direction") or "DEBIT").upper().strip()
    return direction if direction in {"DEBIT", "CREDIT"} else "DEBIT"


def _takeover_summary(signals: list[dict]) -> dict:
    takeover_signals = [item for item in signals if item["category"] == "ACCOUNT_TAKEOVER"]
    takeover_score = min(sum(item["points"] for item in takeover_signals), 100)
    takeover_level = level_from_score(takeover_score)
    recommendation = {
        "LOW": "ALLOW",
        "MEDIUM": "STEP_UP_VERIFY",
        "HIGH": "HOLD_FOR_REVIEW",
        "CRITICAL": "PND_OR_BLOCK",
    }[takeover_level]
    return {
        "detected": takeover_score >= 70,
        "score": takeover_score,
        "level": takeover_level,
        "recommendation": recommendation,
        "indicators": [item["label"] for item in takeover_signals],
    }


def analyze_event(event, behavior=None):
    behavior = behavior or {}
    direction = _normalize_direction(event)

    signals = shared_transaction_signals(event, behavior)
    if direction == "CREDIT":
        signals.extend(credit_signals(event, behavior))
    else:
        signals.extend(debit_signals(event, behavior))

    score = min(sum(item["points"] for item in signals), 100)
    risk_level = level_from_score(score)
    profile_ready = int(behavior.get("trusted_event_count") or 0) >= int(
        (behavior.get("settings") or {}).get("minimum_profile_events", 3)
    )
    confidence = calculate_confidence(score, signals, profile_ready=profile_ready)
    action = action_for_decision(risk_level, confidence)

    reasons = [item["label"] for item in signals]
    return {
        "transaction_direction": direction,
        "risk_score": score,
        "risk_level": risk_level,
        "action": action,
        "recommendation": action,
        "recommended_action": action,
        "reason": ", ".join(reasons) if reasons else "Normal activity",
        "reasons": reasons,
        "signals": signals,
        "confidence": confidence,
        "behavioral_match": not any(item["category"] == "BEHAVIOR" for item in signals),
        "account_takeover": _takeover_summary(signals),
    }
