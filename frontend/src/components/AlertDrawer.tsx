import { motion } from "framer-motion";
import { CheckCircle2, ClipboardCheck, ShieldAlert, X } from "lucide-react";
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
  const timeline = buildInvestigationTimeline(alert, reasons);
  const playbook = selectPlaybook(alert);

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

      <section className="drawer-panel">
        <div className="drawer-section-title">
          <ClipboardCheck size={18} />
          <div>
            <p className="eyebrow">Fraud playbook</p>
            <h3>{playbook.title}</h3>
          </div>
        </div>
        <div className="playbook-grid">
          {playbook.actions.map((action) => (
            <div key={action} className="playbook-step">{action}</div>
          ))}
        </div>
      </section>

      <section className="drawer-panel">
        <div className="drawer-section-title">
          <ShieldAlert size={18} />
          <div>
            <p className="eyebrow">Investigation timeline</p>
            <h3>Event story</h3>
          </div>
        </div>
        <div className="drawer-timeline">
          {timeline.map((item, index) => (
            <div key={`${item.label}-${index}`} className="drawer-timeline-item">
              <span>{index + 1}</span>
              <div>
                <strong>{item.label}</strong>
                <p>{item.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

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

function selectPlaybook(alert: FraudAlert) {
  const text = `${alert.reason} ${alert.recommended_action || ""}`.toLowerCase();
  if (/bot|credential|automation|failed login|many accounts|registrations|velocity/.test(text)) {
    return {
      title: "Bot Attack Response",
      actions: ["Block source IP/device fingerprint", "Throttle login and registration attempts", "Force MFA on affected accounts", "Review shared devices and mule accounts"]
    };
  }
  if (/inflow|deposit|incoming|nips|reported bank|suspicious credit/.test(text)) {
    return {
      title: "Suspicious Inflow Review",
      actions: ["Place temporary PND hold", "Trace source account and narration", "Check linked outflows and beneficiaries", "Escalate to compliance if mule indicators remain"]
    };
  }
  if (/outflow|withdrawal|cashout|repetitive|bulk|beneficiary|transfer|mule/.test(text)) {
    return {
      title: "Repetitive Outflow Control",
      actions: ["Block or hold outgoing transaction", "Review split-transfer pattern", "Check new beneficiary/device history", "Confirm customer intent before release"]
    };
  }
  if (/password|sim swap|new device|login|account takeover|beneficiary/.test(text)) {
    return {
      title: "Account Takeover Response",
      actions: ["Freeze account immediately", "Verify customer identity", "Review password/SIM/device changes", "Reset credentials after confirmed recovery"]
    };
  }
  return {
    title: "General Fraud Review",
    actions: ["Review triggered signals", "Validate customer profile", "Apply recommended decision", "Record final resolution and notes"]
  };
}

function buildInvestigationTimeline(alert: FraudAlert, reasons: string[]) {
  const timeline = [
    { label: "Customer event received", detail: `Boujuron received activity for ${alert.user_id}.` }
  ];

  const addIf = (pattern: RegExp, label: string, detail: string) => {
    if (reasons.some((reason) => pattern.test(reason))) timeline.push({ label, detail });
  };

  addIf(/password/i, "Password activity detected", "Recent credential activity increased account takeover risk.");
  addIf(/sim/i, "SIM change indicator", "SIM-related change was detected before or around the event.");
  addIf(/new device|rooted|emulator|fingerprint|browser/i, "Device intelligence flagged", "Device status, fingerprint, or integrity created extra risk.");
  addIf(/ip|vpn|tor|proxy|country|location|russia/i, "Network/location anomaly", "IP, VPN/TOR, or location signals differed from normal behavior.");
  addIf(/large|amount|transfer|withdrawal|outflow|beneficiary/i, "Money movement risk", "Transaction behavior suggests high-risk transfer or cash-out movement.");
  addIf(/failed login|velocity|bot|credential|automation/i, "Velocity pattern detected", "Repeated attempts or automation-like behavior increased risk.");

  timeline.push({
    label: "System decision applied",
    detail: `${formatLabel(alert.recommended_action || recommendedAction(alert.risk_level, alert.recommended_action))} with ${formatConfidence(alert.confidence)} confidence.`
  });

  if (alert.case_status) {
    timeline.push({
      label: `Case ${formatCaseStatus(alert.case_status)}`,
      detail: alert.closure_note || defaultClosureNote(alert)
    });
  }

  return timeline;
}
