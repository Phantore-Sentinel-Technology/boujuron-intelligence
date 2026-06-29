import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, ChevronRight, Search } from "lucide-react";
import type { FraudAlert, RiskLevel } from "../types";
import { RiskBadge } from "./RiskBadge";
import { AlertDrawer } from "./AlertDrawer";
import { closeCaseWorkflow, confirmFraudCase, markFalsePositiveCase, reverseCaseRestriction, reviewCase } from "../services/api";

const risks: Array<"ALL" | RiskLevel> = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"];

interface FraudTableProps {
  alerts: FraudAlert[];
  loading?: boolean;
  onChanged?: () => Promise<void>;
}

export function FraudTable({ alerts, loading, onChanged }: FraudTableProps) {
  const [query, setQuery] = useState("");
  const [risk, setRisk] = useState<"ALL" | RiskLevel>("ALL");
  const [selected, setSelected] = useState<FraudAlert | null>(null);

  const filtered = useMemo(() => {
    return alerts.filter((alert) => {
      const normalizedQuery = query.toLowerCase().trim();
      const searchable = [
        alert.user_id,
        alert.reason,
        alert.recommended_action || "",
        alert.case_number || "",
        alert.case_status || "",
        alert.analyst_feedback || "",
        alert.timestamp,
        alert.risk_level,
      ].join(" ").toLowerCase();
      const matchesUser = !normalizedQuery || searchable.includes(normalizedQuery);
      const matchesRisk = risk === "ALL" || alert.risk_level === risk;
      return matchesUser && matchesRisk;
    });
  }, [alerts, query, risk]);

  return (
    <section className="table-section fraud-table-section">
      <div className="section-header">
        <div>
          <p className="eyebrow">Alert queue</p>
          <h2>Fraud Decisions</h2>
        </div>
        <div className="table-tools">
          <label className="search-box">
            <Search size={16} />
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search user, reason, case, IP, device" />
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
              <th>Transaction ID</th>
              <th>Direction</th>
              <th>Reason</th>
              <th>Score</th>
              <th>Confidence</th>
              <th>Risk</th>
              <th>Recommended Action</th>
              <th>Tags</th>
              <th>Time</th>
              <th>Case Status</th>
              <th>Analyst Action</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {filtered.map((alert) => (
              <tr key={`${alert.user_id}-${alert.timestamp}-${alert.risk_score}`} onClick={() => setSelected(alert)}>
                <td className="strong">{alert.user_id}</td>
                <td className="mono-cell">{alert.transaction_id || "N/A"}</td>
                <td><span className="direction-pill">{alert.transaction_direction || "DEBIT"}</span></td>
                <td className="reason-cell">
                  <span className="drawer-detail-cue">See investigation drawer detail</span>
                </td>
                <td>{alert.risk_score}</td>
                <td>{formatConfidence(alert.confidence)}</td>
                <td><RiskBadge level={alert.risk_level} /></td>
                <td className="action-cell">{formatAction(alert.recommended_action)}</td>
                <td><AlertTags alert={alert} /></td>
                <td>{formatTime(alert.timestamp)}</td>
                <td>
                  <CaseStatusBadge alert={alert} />
                </td>
                <td>
                  <AnalystActions alert={alert} onChanged={onChanged} />
                </td>
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

function AnalystActions({ alert, onChanged }: { alert: FraudAlert; onChanged?: () => Promise<void> }) {
  const [comment, setComment] = useState("");
  const [saving, setSaving] = useState(false);
  const closed = isClosed(alert.case_status);
  const reversible = canReverse(alert);

  async function runAction(action: "review" | "confirm" | "false-positive" | "reverse" | "close") {
    if (!alert.case_id) return;
    setSaving(true);
    try {
      const note = comment.trim() || undefined;
      if (action === "review") await reviewCase(alert.case_id, note);
      if (action === "confirm") await confirmFraudCase(alert.case_id, note);
      if (action === "false-positive") await markFalsePositiveCase(alert.case_id, note);
      if (action === "reverse") await reverseCaseRestriction(alert.case_id, note);
      if (action === "close") await closeCaseWorkflow(alert.case_id, note);
      setComment("");
      await onChanged?.();
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="dashboard-closure" onClick={(event) => event.stopPropagation()}>
      {closed ? (
        <span className="closure-done"><CheckCircle2 size={14} /> Closed</span>
      ) : (
        <>
          <input
            value={comment}
            onChange={(event) => setComment(event.target.value)}
            placeholder="Analyst note"
          />
          <div className="case-action-buttons">
            <button disabled={!alert.case_id || saving} onClick={() => runAction("review")}>Review</button>
            <button disabled={!alert.case_id || saving} onClick={() => runAction("confirm")}>Confirm Fraud</button>
            <button disabled={!alert.case_id || saving} onClick={() => runAction("false-positive")}>False Positive</button>
            {reversible && <button disabled={!alert.case_id || saving} onClick={() => runAction("reverse")}>Reverse</button>}
            <button className="closure-button" disabled={!alert.case_id || saving} onClick={() => runAction("close")}>
              {saving ? "Saving..." : "Close"}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function CaseStatusBadge({ alert }: { alert: FraudAlert }) {
  if (!alert.case_id) return <span className="muted-text">No case</span>;
  return <span className={isClosed(alert.case_status) ? "closure-done" : "case-open"}>{alert.case_status || "OPEN"}</span>;
}

function AlertTags({ alert }: { alert: FraudAlert }) {
  const tags = [];
  const reasons = countReasons(alert.reason);
  const action = (alert.recommended_action || "").toUpperCase();
  if (alert.risk_level === "CRITICAL" || action.includes("FREEZE")) tags.push("AUTO FREEZE");
  if (alert.risk_level === "HIGH" || action.includes("PND") || action.includes("BLOCK")) tags.push("AUTO PND");
  if (reasons >= 3) tags.push("MULTI-SIGNAL");
  if (/failed login|credential|bot|automation|accounts from/i.test(alert.reason)) tags.push("BOT/ATO");
  if (/withdrawal|cashout|outflow|transfer|beneficiary|mule/i.test(alert.reason)) tags.push("MONEY MOVEMENT");
  if (!tags.length) tags.push(alert.risk_level === "MEDIUM" ? "ANALYST VERIFY" : "WATCH");
  return <div className="alert-tags">{tags.slice(0, 3).map((tag) => <span key={tag}>{tag}</span>)}</div>;
}

function formatAction(action?: string | null) {
  return (action || "REVIEW").replaceAll("_", " ");
}

function formatConfidence(confidence?: number | null) {
  if (confidence === null || confidence === undefined) return "N/A";
  return `${Math.round(confidence > 1 ? confidence : confidence * 100)}%`;
}

function isClosed(status?: string | null) {
  return ["RESOLVED", "ARCHIVED", "CONFIRMED_FRAUD", "FALSE_POSITIVE", "REVERSED", "CLOSED"].includes(status || "");
}

function canReverse(alert: FraudAlert) {
  const action = (alert.recommended_action || "").toUpperCase();
  return Boolean(alert.case_id) && !isClosed(alert.case_status) && (action.includes("HOLD") || action.includes("PND") || action.includes("BLOCK"));
}

function formatTime(timestamp: string) {
  return timestamp?.replace("T", " ").slice(0, 19) || "N/A";
}

function countReasons(reason: string) {
  if (!reason) return 0;
  return reason.split(",").filter(Boolean).length;
}
