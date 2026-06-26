import { Building2, Fingerprint, Globe2, Network, Phone, ShieldCheck } from "lucide-react";

const reputationSignals = [
  {
    icon: Fingerprint,
    title: "Device seen across 4 tenants",
    detail: "The same hashed device fingerprint appears in wallet abuse, failed login bursts and transfer fraud patterns.",
    risk: "HIGH",
    count: "4 tenants"
  },
  {
    icon: Globe2,
    title: "IP linked to 12 suspicious events",
    detail: "Network source is associated with credential testing, VPN transfer attempts and account enumeration.",
    risk: "CRITICAL",
    count: "12 events"
  },
  {
    icon: Phone,
    title: "Phone reputation: high risk",
    detail: "SIM-linked identity changed shortly before new-device login and beneficiary creation.",
    risk: "HIGH",
    count: "3 reports"
  }
];

const tenantExamples = [
  { name: "Wallet A", signal: "Blocked rooted Android device", outcome: "Shared hashed device" },
  { name: "Payments B", signal: "Credential stuffing IP cluster", outcome: "Shared IP reputation" },
  { name: "Lending C", signal: "Mule account pass-through", outcome: "Shared account pattern" },
  { name: "Merchant D", signal: "POS/agent cashout anomaly", outcome: "Shared behavior score" }
];

export function Consortium() {
  return (
    <div className="consortium-page page-grid">
      <section className="insight-panel lab-intro">
        <div>
          <p className="eyebrow">Privacy-preserving intelligence network</p>
          <h2>Africa Fraud Consortium</h2>
          <p>Every participant strengthens the network. Boujuron shares salted hashes and aggregate reputation signals, not raw customer data.</p>
        </div>
        <Network size={30} />
      </section>

      <section className="consortium-hero insight-panel">
        <div>
          <p className="eyebrow">Why this is different</p>
          <h3>Local fraud intelligence that compounds</h3>
          <p>
            Large global platforms can score transactions, but Boujuron is designed to learn from African wallet, transfer,
            device, SIM, agent and mule-account patterns across participating fintechs.
          </p>
        </div>
        <div className="network-value">
          <strong>1 signal</strong>
          <span>can protect many fintechs before the same fraud actor reaches them.</span>
        </div>
      </section>

      <section className="reputation-grid">
        {reputationSignals.map((signal) => {
          const Icon = signal.icon;
          return (
            <article className="insight-panel reputation-card" key={signal.title}>
              <div className="reputation-icon"><Icon size={22} /></div>
              <div>
                <span className={`risk-pill ${signal.risk.toLowerCase()}`}>{signal.risk}</span>
                <h3>{signal.title}</h3>
                <p>{signal.detail}</p>
                <strong>{signal.count}</strong>
              </div>
            </article>
          );
        })}
      </section>

      <section className="insight-panel">
        <div className="section-header">
          <div><p className="eyebrow">Tenant-safe sharing</p><h3>How consortium reputation works</h3></div>
          <ShieldCheck size={22} />
        </div>
        <div className="consortium-flow">
          <div><span>1</span><strong>Detect</strong><p>A fintech confirms fraud against a device, IP, phone or behavior cluster.</p></div>
          <div><span>2</span><strong>Hash</strong><p>Boujuron salts and hashes the signal inside the tenant boundary.</p></div>
          <div><span>3</span><strong>Aggregate</strong><p>The network stores reputation counts, not raw customer identifiers.</p></div>
          <div><span>4</span><strong>Protect</strong><p>Another fintech sees increased risk before authorizing value movement.</p></div>
        </div>
      </section>

      <section className="insight-panel">
        <div className="section-header">
          <div><p className="eyebrow">Network example</p><h3>Shared Intelligence Snapshot</h3></div>
          <Building2 size={22} />
        </div>
        <div className="tenant-signal-list">
          {tenantExamples.map((tenant) => (
            <div className="tenant-signal-row" key={tenant.name}>
              <strong>{tenant.name}</strong>
              <span>{tenant.signal}</span>
              <em>{tenant.outcome}</em>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
