import { Activity, AlertTriangle, Gauge, ShieldAlert, ShieldCheck } from "lucide-react";
import type { AlertStats, FraudAlert } from "../types";
import { StatCard } from "../components/StatCard";
import { FraudTable } from "../components/FraudTable";
import { LiveActivityFeed } from "../components/LiveActivityFeed";
import { RiskDonut, RiskTrend } from "../components/Charts";

interface DashboardProps {
  alerts: FraudAlert[];
  topAlerts: FraudAlert[];
  stats: AlertStats;
  loading: boolean;
}

export function Dashboard({ alerts, topAlerts, stats, loading }: DashboardProps) {
  return (
    <div className="page-grid">
      <section className="stats-grid">
        <StatCard label="Total alerts" value={stats.total} hint="latest events" icon={Activity} />
        <StatCard label="Critical" value={stats.critical} hint="freeze + escalate" icon={ShieldAlert} tone="danger" />
        <StatCard label="High risk" value={stats.high} hint="block and review" icon={AlertTriangle} tone="warn" />
        <StatCard label="Avg score" value={stats.avgScore} hint="risk index" icon={Gauge} />
        <StatCard label="Low risk" value={stats.low} hint="allowed traffic" icon={ShieldCheck} tone="good" />
      </section>

      <div className="analytics-grid">
        <RiskTrend alerts={alerts} />
        <RiskDonut alerts={alerts} />
      </div>

      <div className="content-grid">
        <FraudTable alerts={topAlerts} loading={loading} />
        <LiveActivityFeed alerts={alerts} />
      </div>
    </div>
  );
}
