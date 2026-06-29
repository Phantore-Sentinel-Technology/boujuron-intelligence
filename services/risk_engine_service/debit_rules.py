from .shared_rules import event_flag, signal


def debit_signals(event, behavior):
    signals = []
    amount = float(event.get("amount") or 0)
    event_type = str(event.get("event_type") or "transaction").lower().strip()
    risk_settings = behavior.get("settings", {})
    profile_ready = int(behavior.get("trusted_event_count") or 0) >= int(risk_settings.get("minimum_profile_events", 3))
    average_amount = float(behavior.get("average_amount") or 0)

    if amount >= 2_000_000:
        signals.append(signal("DEBIT", "Extremely large debit", 60, f"Debit amount {amount:.2f} is at least 2,000,000", "CRITICAL"))
    elif amount >= 1_000_000:
        signals.append(signal("DEBIT", "Very large debit", 45, f"Debit amount {amount:.2f} is at least 1,000,000", "STRONG"))
    elif amount >= 500_000:
        signals.append(signal("DEBIT", "Large debit", 30, f"Debit amount {amount:.2f} is at least 500,000"))
    elif amount >= 100_000:
        signals.append(signal("DEBIT", "Moderate high-value debit", 15, f"Debit amount {amount:.2f} is at least 100,000", "WEAK"))

    amount_multiplier = float(risk_settings.get("amount_spike_multiplier", 5))
    minimum_delta = float(risk_settings.get("minimum_amount_delta", 100_000))
    if profile_ready and average_amount > 0 and amount >= max(average_amount * amount_multiplier, average_amount + minimum_delta):
        multiplier = round(amount / average_amount, 1)
        signals.append(signal("BEHAVIOR", "Debit amount spike", 25, f"Debit amount is {multiplier}x the user's historical average"))

    if event_flag(event, "new_beneficiary_added"):
        signals.append(signal("ACCOUNT_TAKEOVER", "New beneficiary before debit", 25, "A new beneficiary was added before this debit"))
    if event_flag(event, "repeated_failed_payments"):
        signals.append(signal("DEBIT", "Repeated failed payment attempts", 25, "Payment attempts repeatedly failed before this debit"))
    if event_type in {"airtime_purchase", "data_purchase"} and amount >= 50_000:
        signals.append(signal("DEBIT", "Airtime/data purchase abuse", 25, "Airtime or data purchase volume is unusually high for wallet activity"))
    if event_type in {"pos_withdrawal", "agent_cashout"} and amount >= 300_000:
        signals.append(signal("DEBIT", "POS/agent transaction anomaly", 30, "High-value agent or POS debit requires review"))

    return signals
