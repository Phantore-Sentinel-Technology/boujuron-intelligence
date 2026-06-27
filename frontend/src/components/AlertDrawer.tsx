import { motion } from "framer-motion";
import { CheckCircle2, ShieldAlert, X } from "lucide-react";
import type { FraudAlert } from "../types";
import { RiskBadge } from "./RiskBadge";
import { ScoreBreakdown } from "./ScoreBreakdown";
import { explainAlert, recommendedAction } from "../utils/risk";

interface AlertDrawerProps {
  alert: FraudAlert;
  onClose: () => void;
}

export function AlertDrawer({ alert, onClose }: AlertDrawerProps) {
  const reasons = alert.reason.split(",").map((reason) => reason.trim()).filter(Boolean);
  const closed = alert.case_status === "RESOLVED" || alert.case_status === "ARCHIVED";
  const closureNote = alert.closure_note || defaultClosureNote(alert);

  return (
    <motion.aside
      className="alert-drawer"
      initial={{ x: 420 }}
      animate={{ x: 0 }}
      exit={{ x: 420 }}
      transition={{ type: "spring", stiffness: 260, damping: 30 }}
    >
      <button className="icon-button close" onClick={onClose} aria-label="Close alert drawer">
        <X size={18} />
      </button>
      <div className="drawer-title">
        <ShieldAlert size={22} />
        <div>
          <p className="eyebrow">Investigation detail</p>
          <div className="drawer-heading-row">
            <h2>{alert.user_id}</h2>
            {closed && (
              <span className="drawer-status-pill">
                <CheckCircle2 size={15} />
                Closed
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="drawer-summary">
        <RiskBadge level={alert.risk_level} />
        <strong>{alert.risk_score}</strong>
        <span>risk score</span>
      </div>

      {closed && (
        <section className="closure-summary-card">
          <div>
            <p className="eyebrow">Closure status</p>
            <strong>{formatCaseStatus(alert.case_status)}</strong>
          </div>
          <div>
            <p className="eyebrow">Analyst feedback</p>
            <strong>{formatLabel(alert.analyst_feedback || "TRUE_FRAUD")}</strong>
          </div>
          <p>{closureNote}</p>
        </section>
      )}

      <dl className="decision-grid">
        <div>
          <dt>Recommended action</dt>
          <dd>{recommendedAction(alert.risk_level, alert.recommended_action)}</dd>
        </div>
        <div>
          <dt>Confidence</dt>
          <dd>{formatConfidence(alert.confidence)}</dd>
        </div>
        <div>
          <dt>Behavioral match</dt>
          <dd>{alert.behavioral_match ? "Yes" : "No"}</dd>
        </div>
        <div>
          <dt>Timestamp</dt>
          <dd>{alert.timestamp}</dd>
        </div>
      </dl>

      <div className="reason-list">
        <p className="eyebrow">Why this decision</p>
        {reasons.map((reason) => (
          <div key={reason} className="reason-item">
            <span />
            {reason}
          </div>
        ))}
      </div>

      <ScoreBreakdown items={explainAlert(alert)} total={Number(alert.risk_score || 0)} />
    </motion.aside>
  );
}

function formatConfidence(confidence?: number | null) {
  if (confidence === null || confidence === undefined) return "N/A";
  const normalized = confidence > 1 ? confidence : confidence * 100;
  return `${Math.round(normalized)}%`;
}

function formatCaseStatus(status?: string | null) {
  return formatLabel(status || "RESOLVED");
}

function formatLabel(value: string) {
  return value.replaceAll("_", " ").toLowerCase().replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function defaultClosureNote(alert: FraudAlert) {
  if (alert.risk_level === "CRITICAL") {
    return "System auto-closed this case after applying immediate freeze/PND controls for a critical, high-confidence fraud pattern.";
  }
  if (alert.risk_level === "HIGH") {
    return "System auto-closed this case after applying immediate PND/block controls for a high-risk fraud pattern.";
  }
  return "Case has been closed with the recorded investigation outcome.";
}
