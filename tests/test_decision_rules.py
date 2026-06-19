from services.dashboard_service.main import compare_rule_value, evaluate_decision_rules


class RuleCursor:
    def __init__(self, rules):
        self.rules = rules

    def execute(self, query, params=None):
        self.query = query
        self.params = params

    def fetchall(self):
        return self.rules


def test_rule_comparisons_support_numeric_and_membership_conditions():
    assert compare_rule_value(1_500_000, "GT", 1_000_000)
    assert compare_rule_value("NIGERIA", "IN", ["nigeria", "ghana"])
    assert compare_rule_value("rooted android", "CONTAINS", "android")
    assert not compare_rule_value(50_000, "GTE", 100_000)


def test_rules_strengthen_but_do_not_weaken_model_decision():
    cursor = RuleCursor([
        (1, "Allow known country", [{"field": "location", "operator": "EQ", "value": "nigeria"}], "ALLOW", 0),
        (2, "Block large new-device transfer", [
            {"field": "amount", "operator": "GT", "value": 1_000_000},
            {"field": "is_new_device", "operator": "EQ", "value": True},
        ], "BLOCK", 15),
    ])
    result = {
        "risk_score": 45,
        "risk_level": "MEDIUM",
        "action": "VERIFY",
        "recommendation": "STEP_UP_VERIFICATION",
        "signals": [],
        "reasons": [],
        "reason": "Normal activity",
    }
    event = {"amount": 1_500_000, "location": "nigeria"}

    evaluation = evaluate_decision_rules(
        cursor,
        organization_id=7,
        event=event,
        result=result,
        device_data={"is_new_device": True},
    )

    assert evaluation["model_action"] == "CHALLENGE"
    assert evaluation["final_action"] == "BLOCK"
    assert evaluation["matched_rules"] == ["Allow known country", "Block large new-device transfer"]
    assert result["action"] == "BLOCK"
    assert result["risk_score"] == 70


def test_allow_rule_cannot_override_high_risk_model():
    cursor = RuleCursor([
        (1, "Allow local activity", [{"field": "location", "operator": "EQ", "value": "nigeria"}], "ALLOW", 0),
    ])
    result = {
        "risk_score": 80,
        "risk_level": "HIGH",
        "action": "BLOCK",
        "recommendation": "BLOCK_AND_REVIEW",
        "signals": [],
        "reasons": [],
        "reason": "High risk",
    }

    evaluation = evaluate_decision_rules(
        cursor,
        organization_id=7,
        event={"location": "nigeria"},
        result=result,
        device_data={"is_new_device": False},
    )

    assert evaluation["final_action"] == "BLOCK"
    assert result["action"] == "BLOCK"
