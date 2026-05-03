from infrastructure.risk_engine.behavior import update_profile
from infrastructure.risk_engine.rules import check_rules
from infrastructure.risk_engine.scoring import calculate_score, get_risk_level
from infrastructure.risk_engine.explain import generate_explanation


def process_event(event, anomaly_score=0, anomaly_reasons=None, ml_score=0):
    """
    Main risk engine:
    Input → event
    Output → score + risk level + explanation
    """

    # 1. update user behavior
    profile = update_profile(event)

    # 2. Rule-base check
    rule_score, rule_reasons = check_rules(event, profile)

    # 3. Combine score
    final_score = calculate_score(
        rule_score,
        anomaly_score,
        ml_score
    )

    # 4. Risk level
    risk_level = get_risk_level(final_score)

    # 5. Explanation
    reasons = generate_explanation(rule_reasons, anomaly_reasons)

    return {
        "user_id": event["user_id"],
        "risk_score": final_score,
        "risk_level": risk_level,
        "reasons": reasons,
        "timestamp": event["timestamp"]
    }
