import { Area, AreaChart, CartesianGrid, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { FraudAlert } from "../types";

const colors = {
  LOW: "#22c55e",
  MEDIUM: "#f59e0b",
  HIGH: "#f97316",
  CRITICAL: "#dc2626"
};

export function RiskDonut({ alerts }: { alerts: FraudAlert[] }) {
  const data = (["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const).map((level) => ({
    name: level,
    value: alerts.filter((alert) => alert.risk_level === level).length
  }));

  return (
    <section className="chart-panel">
      <div className="section-header compact">
        <div>
          <p className="eyebrow">Distribution</p>
          <h2>Risk Mix</h2>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <PieChart>
          <Pie data={data} dataKey="value" nameKey="name" innerRadius={70} outerRadius={102} paddingAngle={4}>
            {data.map((entry) => (
              <Cell key={entry.name} fill={colors[entry.name]} />
            ))}
          </Pie>
          <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8 }} />
        </PieChart>
      </ResponsiveContainer>
      <div className="legend-row">
        {data.map((item) => (
          <span key={item.name}><i style={{ background: colors[item.name] }} />{item.name} {item.value}</span>
        ))}
      </div>
    </section>
  );
}

export function RiskTrend({ alerts }: { alerts: FraudAlert[] }) {
  const data = [...alerts].reverse().slice(-24).map((alert) => ({
    time: alert.timestamp?.slice(11, 16) || "--",
    score: Number(alert.risk_score || 0)
  }));

  return (
    <section className="chart-panel wide">
      <div className="section-header compact">
        <div>
          <p className="eyebrow">Trend</p>
          <h2>Risk Score Movement</h2>
        </div>
      </div>
      <ResponsiveContainer width="100%" height={260}>
        <AreaChart data={data}>
          <defs>
            <linearGradient id="riskGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.45} />
              <stop offset="95%" stopColor="#38bdf8" stopOpacity={0.03} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#1e293b" vertical={false} />
          <XAxis dataKey="time" stroke="#94a3b8" tickLine={false} axisLine={false} />
          <YAxis domain={[0, 100]} stroke="#94a3b8" tickLine={false} axisLine={false} />
          <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155", borderRadius: 8 }} />
          <Area type="monotone" dataKey="score" stroke="#38bdf8" strokeWidth={2} fill="url(#riskGradient)" />
        </AreaChart>
      </ResponsiveContainer>
    </section>
  );
}
