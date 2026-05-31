import { Link } from "react-router-dom";
import type { FraudAlert } from "../types";
import { RiskBadge } from "../components/RiskBadge";

export function Users({ alerts }: { alerts: FraudAlert[] }) {
  const users = Object.values(
    alerts.reduce<Record<string, { id: string; alerts: number; maxScore: number; level: FraudAlert["risk_level"] }>>((acc, alert) => {
      const current = acc[alert.user_id] || { id: alert.user_id, alerts: 0, maxScore: 0, level: "LOW" };
      const score = Number(alert.risk_score || 0);
      acc[alert.user_id] = {
        id: alert.user_id,
        alerts: current.alerts + 1,
        maxScore: Math.max(current.maxScore, score),
        level: score >= current.maxScore ? alert.risk_level : current.level
      };
      return acc;
    }, {})
  ).sort((a, b) => b.maxScore - a.maxScore);

  return (
    <section className="insight-panel">
      <div className="section-header">
        <div>
          <p className="eyebrow">Behavioral profiles</p>
          <h2>User Intelligence</h2>
        </div>
      </div>
      <div className="user-grid">
        {users.map((user) => (
          <Link key={user.id} className="user-row" to={`/customers/${encodeURIComponent(user.id)}`}>
            <div>
              <strong>{user.id}</strong>
              <span>{user.alerts} alerts observed</span>
            </div>
            <span>{user.maxScore}</span>
            <RiskBadge level={user.level} />
          </Link>
        ))}
        {users.length === 0 && <div className="empty-state">No behavioral profiles yet.</div>}
      </div>
    </section>
  );
}
