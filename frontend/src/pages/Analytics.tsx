import type { AlertStats, FraudAlert } from "../types";
import { RiskDonut, RiskTrend } from "../components/Charts";

interface AnalyticsProps {
  alerts: FraudAlert[];
  stats: AlertStats;
}

export function Analytics({ alerts, stats }: AnalyticsProps) {
  const topUsers = Object.entries(
    alerts.reduce<Record<string, number>>((acc, alert) => {
      acc[alert.user_id] = (acc[alert.user_id] || 0) + 1;
      return acc;
    }, {})
  ).sort((a, b) => b[1] - a[1]).slice(0, 6);

  return (
    <div className="page-grid">
      <div className="analytics-grid">
        <RiskTrend alerts={alerts} />
        <RiskDonut alerts={alerts} />
      </div>

      <section className="insight-panel">
        <div className="section-header compact">
          <div>
            <p className="eyebrow">Threat analytics</p>
            <h2>Operational Summary</h2>
          </div>
        </div>
        <div className="insight-grid">
          <div><span>Total</span><strong>{stats.total}</strong></div>
          <div><span>Critical rate</span><strong>{stats.total ? Math.round((stats.critical / stats.total) * 100) : 0}%</strong></div>
          <div><span>High+ queue</span><strong>{stats.high + stats.critical}</strong></div>
          <div><span>Average score</span><strong>{stats.avgScore}</strong></div>
        </div>
      </section>

      <section className="insight-panel">
        <div className="section-header compact">
          <div>
            <p className="eyebrow">User concentration</p>
            <h2>Most Active Accounts</h2>
          </div>
        </div>
        <div className="rank-list">
          {topUsers.map(([user, count]) => (
            <div key={user}>
              <strong>{user}</strong>
              <span>{count} alerts</span>
            </div>
          ))}
          {topUsers.length === 0 && <div className="empty-state slim">No user activity yet.</div>}
        </div>
      </section>
    </div>
  );
}
