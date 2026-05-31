import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronRight, Search } from "lucide-react";
import type { FraudAlert, RiskLevel } from "../types";
import { RiskBadge } from "./RiskBadge";
import { AlertDrawer } from "./AlertDrawer";

const risks: Array<"ALL" | RiskLevel> = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"];

interface FraudTableProps {
  alerts: FraudAlert[];
  loading?: boolean;
}

export function FraudTable({ alerts, loading }: FraudTableProps) {
  const [query, setQuery] = useState("");
  const [risk, setRisk] = useState<"ALL" | RiskLevel>("ALL");
  const [selected, setSelected] = useState<FraudAlert | null>(null);

  const filtered = useMemo(() => {
    return alerts.filter((alert) => {
      const matchesUser = alert.user_id.toLowerCase().includes(query.toLowerCase());
      const matchesRisk = risk === "ALL" || alert.risk_level === risk;
      return matchesUser && matchesRisk;
    });
  }, [alerts, query, risk]);

  return (
    <section className="table-section">
      <div className="section-header">
        <div>
          <p className="eyebrow">Alert queue</p>
          <h2>Fraud Decisions</h2>
        </div>
        <div className="table-tools">
          <label className="search-box">
            <Search size={16} />
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search account" />
          </label>
          <div className="segmented">
            {risks.map((item) => (
              <button key={item} className={risk === item ? "active" : ""} onClick={() => setRisk(item)}>
                {item}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>User</th>
              <th>Score</th>
              <th>Risk</th>
              <th>Confidence</th>
              <th>Signals</th>
              <th>Action</th>
              <th>Reason</th>
              <th>Time</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {filtered.map((alert) => (
              <tr key={`${alert.user_id}-${alert.timestamp}-${alert.risk_score}`} onClick={() => setSelected(alert)}>
                <td className="strong">{alert.user_id}</td>
                <td>{alert.risk_score}</td>
                <td><RiskBadge level={alert.risk_level} /></td>
                <td>{formatConfidence(alert.confidence)}</td>
                <td>{alert.signals_triggered ?? countReasons(alert.reason)}</td>
                <td className="action-cell">{formatAction(alert.recommended_action)}</td>
                <td className="reason-cell">{alert.reason}</td>
                <td>{formatTime(alert.timestamp)}</td>
                <td><ChevronRight size={16} /></td>
              </tr>
            ))}
          </tbody>
        </table>
        {!loading && filtered.length === 0 && <div className="empty-state">No matching fraud alerts yet.</div>}
        {loading && <div className="empty-state">Loading intelligence stream...</div>}
      </div>

      <AnimatePresence>
        {selected && (
          <motion.div className="drawer-backdrop" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
            <AlertDrawer alert={selected} onClose={() => setSelected(null)} />
          </motion.div>
        )}
      </AnimatePresence>
    </section>
  );
}

function formatAction(action?: string | null) {
  return (action || "REVIEW").replaceAll("_", " ");
}

function formatConfidence(confidence?: number | null) {
  if (confidence === null || confidence === undefined) return "N/A";
  return `${Math.round(confidence * 100)}%`;
}

function formatTime(timestamp: string) {
  return timestamp?.replace("T", " ").slice(0, 19) || "N/A";
}

function countReasons(reason: string) {
  if (!reason) return 0;
  return reason.split(",").filter(Boolean).length;
}
