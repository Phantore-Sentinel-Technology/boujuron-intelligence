import { motion } from "framer-motion";
import { ShieldAlert, X } from "lucide-react";
import type { FraudAlert } from "../types";
import { RiskBadge } from "./RiskBadge";

interface AlertDrawerProps {
  alert: FraudAlert;
  onClose: () => void;
}

export function AlertDrawer({ alert, onClose }: AlertDrawerProps) {
  const reasons = alert.reason.split(",").map((reason) => reason.trim()).filter(Boolean);

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
          <h2>{alert.user_id}</h2>
        </div>
      </div>

      <div className="drawer-summary">
        <RiskBadge level={alert.risk_level} />
        <strong>{alert.risk_score}</strong>
        <span>risk score</span>
      </div>

      <dl className="decision-grid">
        <div>
          <dt>Recommended action</dt>
          <dd>{(alert.recommended_action || "REVIEW").replaceAll("_", " ")}</dd>
        </div>
        <div>
          <dt>Confidence</dt>
          <dd>{alert.confidence ? `${Math.round(alert.confidence * 100)}%` : "N/A"}</dd>
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
    </motion.aside>
  );
}
