import type { FraudAlert, ScoreBreakdownItem } from "../types";

export function recommendedAction(level: FraudAlert["risk_level"], fallback?: string | null) {
  if (fallback) {
    const normalized = fallback.toUpperCase();
    if (normalized.includes("PND") || normalized.includes("BLOCK")) return "Account PND / Block";
    if (normalized.includes("HOLD")) return "Hold Account for Review";
    return fallback.replaceAll("_", " ");
  }
  if (level === "LOW") return "Allow";
  if (level === "MEDIUM") return "Step-Up Verification";
  if (level === "HIGH") return "Hold Account for Review";
  return "Account PND / Block";
}

export function explainAlert(alert: FraudAlert): ScoreBreakdownItem[] {
  const total = Number(alert.risk_score || 0);
  let remaining = total;
  const weights: Array<[string, number]> = [
    ["rooted", 25],
    ["tor", 20],
    ["location", 15],
    ["behavior", 10],
    ["velocity", 12],
    ["device", 15],
    ["network", 12],
    ["ip", 10]
  ];

  const reasons = alert.reason.split(",").map((reason) => reason.trim()).filter(Boolean);
  const items = reasons.map((reason) => {
    const lower = reason.toLowerCase();
    const points = Math.min(weights.find(([keyword]) => lower.includes(keyword))?.[1] ?? 8, Math.max(remaining, 0));
    remaining -= points;
    return { label: reason, points, evidence: reason };
  });

  if (remaining > 0) {
    items.push({ label: "Model Baseline", points: remaining, evidence: "Residual risk from combined scoring signals" });
  }

  return items;
}
