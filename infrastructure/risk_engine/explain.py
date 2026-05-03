def generate_explanation(rule_reasons, anomaly_reasons=None):
    reasons = []

    if rule_reasons:
        reasons.extend(rule_reasons)

    if anomaly_reasons:
        reasons.extend(anomaly_reasons)

    if not reasons:
        reasons.append("Normal behavior")

    return reasons

