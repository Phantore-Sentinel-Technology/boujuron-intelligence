import { Activity, AlertTriangle, Bot, Gauge, LockKeyhole, ShieldAlert, ShieldCheck, UserRoundSearch } from "lucide-react";
import { useMemo } from "react";
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
  reloadAlerts: () => Promise<void>;
}

export function Dashboard({ alerts, topAlerts, stats, loading, reloadAlerts }: DashboardProps) {
  const operational = useMemo(() => buildOperationalMetrics(alerts), [alerts]);

  return (
    <div className="page-grid">
      <section className="stats-grid">
        <StatCard label="Total alerts" value={stats.total} hint="latest events" icon={Activity} />
        <StatCard label="Critical" value={stats.critical} hint="freeze + escalate" icon={ShieldAlert} tone="danger" />
        <StatCard label="High risk" value={stats.high} hint="block and review" icon={AlertTriangle} tone="warn" />
        <StatCard label="Avg score" value={stats.avgScore} hint="risk index" icon={Gauge} />
        <StatCard label="Low risk" value={stats.low} hint="allowed traffic" icon={ShieldCheck} tone="good" />
      </section>

      <section className="ops-grid">
        <StatCard label="Open investigations" value={operational.openInvestigations} hint="analyst workload" icon={UserRoundSearch} tone="warn" />
        <StatCard label="Blocked today" value={operational.blockedToday} hint="auto-PND / freeze" icon={LockKeyhole} tone="danger" />
        <StatCard label="ATO attempts" value={operational.atoAttempts} hint="account takeover signals" icon={ShieldAlert} tone="danger" />
        <StatCard label="Bot attacks" value={operational.botAttempts} hint="credential abuse patterns" icon={Bot} tone="warn" />
      </section>

      <div className="analytics-grid">
        <RiskTrend alerts={alerts} />
        <RiskDonut alerts={alerts} />
      </div>

      <div className="content-grid">
        <FraudTable alerts={topAlerts} loading={loading} onChanged={reloadAlerts} />
        <LiveActivityFeed alerts={alerts} />
      </div>
    </div>
  );
}

function buildOperationalMetrics(alerts: FraudAlert[]) {
  const today = new Date().toISOString().slice(0, 10);
  const openInvestigations = alerts.filter((alert) => alert.case_status && !["RESOLVED", "ARCHIVED"].includes(alert.case_status)).length;
  const blockedToday = alerts.filter((alert) => {
    const action = (alert.recommended_action || "").toUpperCase();
    const isToday = alert.timestamp?.slice(0, 10) === today;
    return isToday && (alert.risk_level === "CRITICAL" || action.includes("BLOCK") || action.includes("FREEZE") || action.includes("PND"));
  }).length;
  const atoAttempts = alerts.filter((alert) => /account takeover|password|sim swap|new device|failed login|login velocity|beneficiary/i.test(alert.reason)).length;
  const botAttempts = alerts.filter((alert) => /bot|credential|automation|failed login|many accounts|registrations|velocity/i.test(alert.reason)).length;

  return { openInvestigations, blockedToday, atoAttempts, botAttempts };
}
