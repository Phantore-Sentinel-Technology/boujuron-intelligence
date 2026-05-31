import type { RiskLevel } from "../types";

export function RiskBadge({ level }: { level: RiskLevel }) {
  return <span className={`risk-badge ${level.toLowerCase()}`}>{level}</span>;
}
