import { Activity, AlertTriangle, Gauge, RotateCcw, ShieldAlert, ShieldCheck, UserRoundSearch, XCircle } from "lucide-react";
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
        <StatCard label="Total cases" value={operational.totalCases} hint="banking review queue" icon={UserRoundSearch} tone="warn" />
        <StatCard label="Open cases" value={operational.openInvestigations} hint="analyst workload" icon={AlertTriangle} tone="warn" />
        <StatCard label="Critical cases" value={operational.criticalCases} hint="PND/block candidates" icon={ShieldAlert} tone="danger" />
        <StatCard label="High risk cases" value={operational.highCases} hint="hold for review" icon={Gauge} tone="warn" />
        <StatCard label="False positives" value={operational.falsePositives} hint="customer friction reduced" icon={XCircle} />
        <StatCard label="Reversed" value={operational.reversedTransactions} hint="restrictions lifted" icon={RotateCcw} tone="good" />
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
  const caseAlerts = alerts.filter((alert) => alert.case_id);
  const closedStatuses = ["RESOLVED", "ARCHIVED", "CONFIRMED_FRAUD", "FALSE_POSITIVE", "REVERSED", "CLOSED"];
  const totalCases = new Set(caseAlerts.map((alert) => alert.case_id)).size;
  const openInvestigations = caseAlerts.filter((alert) => !closedStatuses.includes(alert.case_status || "")).length;
  const criticalCases = caseAlerts.filter((alert) => alert.risk_level === "CRITICAL").length;
  const highCases = caseAlerts.filter((alert) => alert.risk_level === "HIGH").length;
  const falsePositives = caseAlerts.filter((alert) => alert.case_status === "FALSE_POSITIVE" || alert.analyst_feedback === "FALSE_POSITIVE").length;
  const reversedTransactions = caseAlerts.filter((alert) => alert.case_status === "REVERSED").length;

  return { totalCases, openInvestigations, criticalCases, highCases, falsePositives, reversedTransactions };
}
