def calculate_score(rule_score, anomaly_score=0, ml_score=0):
    """
    Combine different signals into final score
    """

    final_score = rule_score + anomaly_score + ml_score

    if final_score > 100:
        final_score = 100

    return final_score


def get_risk_level(score):
    if score >= 80:
        return "HIGH"
    elif score >= 50:
        return "MEDIUM"
    return "LOW"

