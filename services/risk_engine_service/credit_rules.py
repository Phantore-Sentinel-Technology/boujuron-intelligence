from .shared_rules import event_flag, event_int, signal


def credit_signals(event, behavior):
    signals = []
    amount = float(event.get("amount") or 0)
    event_type = str(event.get("event_type") or "transaction").lower().strip()
    risk_settings = behavior.get("settings", {})
    profile_ready = int(behavior.get("trusted_event_count") or 0) >= int(risk_settings.get("minimum_profile_events", 3))
    average_amount = float(behavior.get("average_amount") or 0)

    if amount >= 5_000_000:
        signals.append(signal("CREDIT", "Extremely large incoming credit", 55, f"Credit amount {amount:.2f} is at least 5,000,000", "CRITICAL"))
    elif amount >= 2_000_000:
        signals.append(signal("CREDIT", "Very large incoming credit", 40, f"Credit amount {amount:.2f} is at least 2,000,000", "STRONG"))
    elif amount >= 500_000:
        signals.append(signal("CREDIT", "Unusual incoming amount", 25, f"Credit amount {amount:.2f} is unusually high"))

    if profile_ready and average_amount > 0 and amount >= max(average_amount * 8, average_amount + float(risk_settings.get("minimum_amount_delta", 100_000))):
        signals.append(signal("BEHAVIOR", "Credit amount spike", 25, "Incoming amount is far above the user's historical average"))

    rapid_credits = event_int(event, "rapid_credit_count")
    different_senders = event_int(event, "different_sender_count")
    suspicious_debits = event_int(event, "debits_after_credit_count")
    dormant_days = event_int(event, "dormant_days")
    credit_frequency = event_int(event, "credit_frequency_count")

    if rapid_credits >= 3 and different_senders >= 2:
        signals.append(signal("CREDIT", "Multiple rapid credits from different sources", 40, f"{rapid_credits} rapid credits from {different_senders} senders", "STRONG"))
    if suspicious_debits >= 1:
        signals.append(signal("CREDIT", "Credits followed quickly by suspicious debits", 45, "Incoming funds were followed by suspicious outgoing movement", "STRONG"))
    if event_flag(event, "suspicious_sender"):
        signals.append(signal("CREDIT", "Suspicious sender pattern", 35, "Sender pattern is associated with risky inflows", "STRONG"))
    if event_flag(event, "mule_account_suspected"):
        signals.append(signal("CREDIT", "Mule account behavior", 45, "Account behavior resembles mule pass-through movement", "STRONG"))
    if dormant_days >= 60 and amount >= 500_000:
        signals.append(signal("CREDIT", "Dormant account large credit", 35, f"Account was dormant for {dormant_days} days before receiving a large credit", "STRONG"))
    if credit_frequency >= 8:
        signals.append(signal("CREDIT", "Unusual credit frequency", 30, f"{credit_frequency} credits in a short monitoring window"))
    if event_type in {"chargeback", "reversal_risk"} or event_flag(event, "chargeback_risk"):
        signals.append(signal("CREDIT", "Reversal/chargeback risk indicator", 35, "Credit carries reversal or chargeback risk", "STRONG"))
    if str(event.get("channel") or event.get("metadata", {}).get("channel") or "").lower() in {"crypto", "unknown_agent", "unverified_partner"}:
        signals.append(signal("CREDIT", "Credit from high-risk channel", 30, "Incoming credit came through a high-risk channel"))

    return signals
