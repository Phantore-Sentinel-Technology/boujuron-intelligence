import { useEffect, useState } from "react";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Download, FileText, Globe2 } from "lucide-react";
import type { AnalystPerformance, AnalyticsOverview, FraudHeatMapPoint, RiskDistributionPoint, TrendPoint } from "../types";
import { downloadExport, getAnalystPerformance, getAnalyticsOverview, getAnalyticsTrends, getFraudHeatMap, getRiskDistribution } from "../services/api";

const riskColors = {
  LOW: "#22c55e",
  MEDIUM: "#f59e0b",
  HIGH: "#f97316",
  CRITICAL: "#dc2626"
};

const emptyOverview: AnalyticsOverview = {
  total_events: 0,
  fraud_alerts: 0,
  confirmed_fraud_cases: 0,
  fraud_prevention_rate: 0,
  false_positive_rate: 0,
  average_investigation_minutes: 0,
  cases_resolved: 0
};

export function Executive() {
  const [overview, setOverview] = useState<AnalyticsOverview>(emptyOverview);
  const [trends, setTrends] = useState<TrendPoint[]>([]);
  const [riskDistribution, setRiskDistribution] = useState<RiskDistributionPoint[]>([]);
  const [analysts, setAnalysts] = useState<AnalystPerformance[]>([]);
  const [heatMap, setHeatMap] = useState<FraudHeatMapPoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;

    const loadExecutiveData = async () => {
      try {
        const overviewData = await getAnalyticsOverview();
        if (mounted) setOverview(overviewData);
      } catch {
        // Keep the last successful values visible during brief free-tier API delays.
      }

      try {
        const trendsData = await getAnalyticsTrends();
        if (mounted) setTrends(trendsData);
      } catch {
        // Optional chart data retries on the next refresh cycle.
      }

      try {
        const distributionData = await getRiskDistribution();
        if (mounted) setRiskDistribution(distributionData);
      } catch {
        // Optional chart data retries on the next refresh cycle.
      }

      try {
        const analystData = await getAnalystPerformance();
        if (mounted) setAnalysts(analystData);
      } catch {
        // Optional chart data retries on the next refresh cycle.
      }

      try {
        const heatData = await getFraudHeatMap();
        if (mounted) setHeatMap(heatData);
      } catch {
        // Optional chart data retries on the next refresh cycle.
      }

      if (mounted) setLoading(false);
    };

    loadExecutiveData();
    const timer = window.setInterval(loadExecutiveData, 8000);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, []);

  return (
    <div className="page-grid">
      <section className="executive-hero">
        <div>
          <p className="eyebrow">Executive intelligence</p>
          <h2>Fraud Performance Overview</h2>
        </div>
        <div className="export-actions">
          <button onClick={() => downloadExport("/export/fraud-alerts.csv", "fraud-alerts.csv")}><Download size={16} /> Alerts CSV</button>
          <button onClick={() => downloadExport("/export/cases.csv", "cases.csv")}><Download size={16} /> Cases CSV</button>
          <button onClick={() => downloadExport("/export/monthly-report.csv", "monthly-report.csv")}><Download size={16} /> Monthly CSV</button>
          <button onClick={() => downloadExport("/reports/monthly.pdf", "monthly-fraud-report.pdf")}><FileText size={16} /> PDF Report</button>
        </div>
      </section>

      <section className="executive-kpi-grid">
        <Kpi label="Total Events Processed" value={overview.total_events.toLocaleString()} />
        <Kpi label="Fraud Alerts Generated" value={overview.fraud_alerts.toLocaleString()} />
        <Kpi label="Confirmed Fraud Cases" value={overview.confirmed_fraud_cases.toLocaleString()} />
        <Kpi label="Fraud Prevention Rate" value={`${overview.fraud_prevention_rate}%`} />
        <Kpi label="False Positive Rate" value={`${overview.false_positive_rate}%`} />
        <Kpi label="Avg Investigation Time" value={`${overview.average_investigation_minutes}m`} />
      </section>

      <div className="executive-grid">
        <section className="chart-panel">
          <div className="section-header compact">
            <div>
              <p className="eyebrow">Fraud trends</p>
              <h2>Alerts Over Time</h2>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <AreaChart data={trends}>
              <defs>
                <linearGradient id="executiveTrend" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.45} />
                  <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.03} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#1e293b" vertical={false} />
              <XAxis dataKey="label" stroke="#94a3b8" tickLine={false} axisLine={false} />
              <YAxis stroke="#94a3b8" tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8 }} />
              <Area dataKey="value" stroke="#38bdf8" strokeWidth={2} fill="url(#executiveTrend)" />
            </AreaChart>
          </ResponsiveContainer>
          {!loading && trends.length === 0 && <div className="chart-empty">No fraud trend data yet.</div>}
        </section>

        <section className="chart-panel">
          <div className="section-header compact">
            <div>
              <p className="eyebrow">Risk distribution</p>
              <h2>Risk Mix</h2>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={riskDistribution} dataKey="count" nameKey="level" innerRadius={68} outerRadius={102} paddingAngle={4}>
                {riskDistribution.map((item) => <Cell key={item.level} fill={riskColors[item.level]} />)}
              </Pie>
              <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8 }} />
            </PieChart>
          </ResponsiveContainer>
          {!loading && riskDistribution.every((item) => item.count === 0) && <div className="chart-empty">No risk mix data yet.</div>}
        </section>
      </div>

      <div className="executive-grid">
        <section className="chart-panel">
          <div className="section-header compact">
            <div>
              <p className="eyebrow">Analyst performance</p>
              <h2>Case Throughput</h2>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={analysts}>
              <CartesianGrid stroke="#1e293b" vertical={false} />
              <XAxis dataKey="analyst" stroke="#94a3b8" tickLine={false} axisLine={false} />
              <YAxis stroke="#94a3b8" tickLine={false} axisLine={false} />
              <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8 }} />
              <Bar dataKey="assigned_cases" fill="#38bdf8" radius={[6, 6, 0, 0]} />
              <Bar dataKey="resolved_cases" fill="#22c55e" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
          {!loading && analysts.length === 0 && <div className="chart-empty">No case throughput yet.</div>}
        </section>

        <section className="insight-panel heat-panel">
          <div className="section-header compact">
            <div>
              <p className="eyebrow">Attack geography</p>
              <h2>Fraud Heat Map</h2>
            </div>
            <Globe2 size={22} />
          </div>
          <div className="heat-list">
            {heatMap.map((item) => (
              <div key={item.location} className="heat-row">
                <div>
                  <strong>{item.location}</strong>
                  <span>{item.alerts} alerts / avg risk {item.average_risk}</span>
                </div>
                <i style={{ width: `${Math.min(item.average_risk, 100)}%`, background: riskColors[item.highest_risk] }} />
              </div>
            ))}
            {heatMap.length === 0 && <div className="empty-state slim">No geographic activity yet.</div>}
          </div>
        </section>
      </div>
    </div>
  );
}

function Kpi({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
