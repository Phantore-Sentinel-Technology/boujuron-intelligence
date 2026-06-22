import { useMemo, useState } from "react";
import { CheckCircle2, FlaskConical, Play, ShieldAlert } from "lucide-react";
import { scoreRiskEvent } from "../services/api";
import type { RiskDecision } from "../types";
import { RiskBadge } from "../components/RiskBadge";

const scenarios = [
  {
    id: "airtime",
    name: "Normal Airtime",
    summary: "Familiar mobile activity with a small purchase.",
    payload: {
      user_id: "maripay_customer_101", event_type: "airtime_purchase", amount: 2000,
      device_type: "iphone", device_id: "maripay-iphone-101", platform: "ios",
      operating_system: "iOS 18", ip: "102.88.45.101", location: "lagos, nigeria", network: "MOBILE"
    }
  },
  {
    id: "vpn",
    name: "VPN Transfer",
    summary: "Higher-value wallet transfer routed through a VPN.",
    payload: {
      user_id: "maripay_customer_202", event_type: "wallet_transfer", amount: 180000,
      device_type: "android", device_id: "maripay-android-202", platform: "android",
      operating_system: "Android 15", ip: "197.210.10.202", location: "abuja, nigeria", network: "VPN"
    }
  },
  {
    id: "takeover",
    name: "Account Takeover",
    summary: "SIM change, failed logins, rooted device and large transfer.",
    payload: {
      user_id: "maripay_customer_303", event_type: "wallet_transfer", amount: 750000,
      device_type: "android", device_id: "unknown-android-303", platform: "android",
      operating_system: "Android 14", ip: "45.90.12.10", location: "russia", network: "VPN",
      password_changed_recently: true, sim_swap_detected: true, failed_login_count: 8, is_rooted: true
    }
  },
  {
    id: "emulator",
    name: "Manipulated Device",
    summary: "Emulator, browser tampering, failed attestation and TOR.",
    payload: {
      user_id: "maripay_customer_404", event_type: "login", amount: 0,
      device_type: "android emulator", device_id: "emulator-404", platform: "android",
      operating_system: "Android 14", browser: "Chrome", ip: "45.90.12.10",
      location: "unknown", network: "TOR", is_emulator: true,
      browser_tampering: true, device_attestation: "FAILED"
    }
  }
];

export function DecisionLab() {
  const [selectedId, setSelectedId] = useState(scenarios[0].id);
  const [result, setResult] = useState<RiskDecision | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const selected = useMemo(() => scenarios.find((item) => item.id === selectedId) || scenarios[0], [selectedId]);

  async function runScenario() {
    setRunning(true);
    setError("");
    setResult(null);
    try {
      setResult(await scoreRiskEvent({
        ...selected.payload,
        transaction_id: `demo-${selected.id}-${Date.now()}`
      }));
    } catch {
      setError("The decision could not be completed. Confirm the backend is awake and try again.");
    } finally {
      setRunning(false);
    }
  }

  return (
    <div className="decision-lab page-grid">
      <section className="insight-panel lab-intro">
        <div>
          <p className="eyebrow">Controlled fraud simulation</p>
          <h2>MariPay Decision Lab</h2>
          <p>Run a realistic wallet event through Boujuron and inspect the decision before value leaves the account.</p>
        </div>
        <FlaskConical size={28} />
      </section>

      <section className="lab-workspace">
        <div className="scenario-list">
          {scenarios.map((scenario) => (
            <button
              className={`scenario-option ${scenario.id === selectedId ? "active" : ""}`}
              key={scenario.id}
              onClick={() => { setSelectedId(scenario.id); setResult(null); }}
            >
              <strong>{scenario.name}</strong>
              <span>{scenario.summary}</span>
            </button>
          ))}
        </div>

        <div className="insight-panel scenario-console">
          <div className="section-header">
            <div><p className="eyebrow">Incoming event</p><h3>{selected.name}</h3></div>
            <button className="primary-button" onClick={runScenario} disabled={running}>
              <Play size={16} />{running ? "Scoring..." : "Run decision"}
            </button>
          </div>
          <div className="event-preview">
            {Object.entries(selected.payload).map(([key, value]) => (
              <div key={key}><span>{key.replaceAll("_", " ")}</span><strong>{String(value)}</strong></div>
            ))}
          </div>
          {error && <div className="form-error">{error}</div>}
        </div>
      </section>

      <section className="insight-panel decision-result">
        {!result && <div className="empty-state lab-empty"><ShieldAlert size={24} /><span>Run a scenario to see Boujuron’s decision and evidence.</span></div>}
        {result && <>
          <div className="decision-result-head">
            <div><p className="eyebrow">Decision #{result.action_decision_id || result.decision_id}</p><h2>{result.action}</h2></div>
            <div className="decision-score"><RiskBadge level={result.risk_level} /><strong>{result.risk_score}</strong><span>{result.confidence}% confidence</span></div>
          </div>
          <div className="decision-summary-grid">
            <div><span>Recommendation</span><strong>{result.recommendation.replaceAll("_", " ")}</strong></div>
            <div><span>Device state</span><strong>{result.device_intelligence?.status || "Not available"}</strong></div>
            <div><span>Account takeover</span><strong>{result.account_takeover?.detected ? "Detected" : "Not detected"}</strong></div>
            <div><span>Matched policies</span><strong>{result.matched_rules.length}</strong></div>
          </div>
          <div className="decision-evidence">
            {result.signals.map((signal) => (
              <div key={`${signal.category}-${signal.label}`}>
                <CheckCircle2 size={16} />
                <div><strong>{signal.label} <em>+{signal.points}</em></strong><span>{signal.evidence}</span></div>
              </div>
            ))}
            {!result.signals.length && <div className="safe-decision"><CheckCircle2 size={18} />No suspicious signals detected.</div>}
          </div>
        </>}
      </section>
    </div>
  );
}
