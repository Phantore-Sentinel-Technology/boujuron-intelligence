import { useEffect, useMemo, useState } from "react";
import { Code2, Copy, KeyRound, RadioTower, RotateCcw, Webhook } from "lucide-react";
import {
  createAlertDestination,
  createClientApiKey,
  getAlertDestinations,
  getClientApiKeys,
  getPortalUsage,
  rotateClientApiKey
} from "../services/api";
import type { AlertDestination, ApiUsage, ClientApiKey } from "../types";

const sampleRequest = {
  user_id: "customer_102",
  transaction_id: "txn_102_001",
  event_type: "wallet_transfer",
  amount: 750000,
  device_id: "android-new-102",
  device_type: "android",
  ip: "197.210.10.202",
  location: "lagos, nigeria",
  network: "VPN",
  password_changed_recently: true,
  new_beneficiary_added: true
};

const sampleResponse = {
  risk_score: 94,
  risk_level: "CRITICAL",
  action: "BLOCK",
  recommendation: "LOCK_ACCOUNT_AND_ESCALATE",
  reasons: ["New device after password reset", "VPN usage detected", "New beneficiary before transfer"]
};

export function DeveloperApi() {
  const [keys, setKeys] = useState<ClientApiKey[]>([]);
  const [usage, setUsage] = useState<ApiUsage | null>(null);
  const [destinations, setDestinations] = useState<AlertDestination[]>([]);
  const [keyName, setKeyName] = useState("Production API");
  const [destinationName, setDestinationName] = useState("Fraud operations");
  const [destinationTarget, setDestinationTarget] = useState("");
  const [createdKey, setCreatedKey] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);

  const curlExample = useMemo(() => `curl -X POST https://boujuron-intelligence.fly.dev/risk-score \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: bj_live_your_client_key" \\
  -H "Idempotency-Key: txn_102_001" \\
  -d '${JSON.stringify(sampleRequest, null, 2)}'`, []);

  async function load() {
    setLoading(true);
    try {
      const [keyRows, usageData, destinationRows] = await Promise.all([
        getClientApiKeys(),
        getPortalUsage(),
        getAlertDestinations()
      ]);
      setKeys(keyRows);
      setUsage(usageData);
      setDestinations(destinationRows);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreateKey() {
    setMessage("");
    const created = await createClientApiKey(keyName);
    setCreatedKey(created.api_key || "");
    setKeys((current) => [created, ...current]);
    setMessage("API key created. Copy it now; only the prefix will remain visible later.");
  }

  async function handleRotateKey(keyId: number) {
    setMessage("");
    const rotated = await rotateClientApiKey(keyId);
    setCreatedKey(rotated.api_key || "");
    await load();
    setMessage("API key rotated. Update the client integration with the new value.");
  }

  async function handleCreateDestination() {
    setMessage("");
    await createAlertDestination({
      name: destinationName,
      channel: "WEBHOOK",
      target: destinationTarget,
      minimum_risk: "HIGH",
      enabled: true
    });
    setDestinationTarget("");
    await load();
    setMessage("Webhook destination added for high-risk alerts.");
  }

  function copy(value: string) {
    navigator.clipboard.writeText(value);
    setMessage("Copied to clipboard.");
  }

  return (
    <div className="developer-api page-grid">
      <section className="insight-panel lab-intro">
        <div>
          <p className="eyebrow">API-first fraud infrastructure</p>
          <h2>Developer API</h2>
          <p>Boujuron can sit directly inside a fintech transaction flow, return a real-time decision, and notify operations before value leaves the wallet.</p>
        </div>
        <Code2 size={28} />
      </section>

      <section className="developer-grid">
        <div className="insight-panel">
          <div className="section-header">
            <div><p className="eyebrow">Client access</p><h3>API Keys</h3></div>
            <KeyRound size={22} />
          </div>
          <div className="api-inline-form">
            <input value={keyName} onChange={(event) => setKeyName(event.target.value)} />
            <button className="primary-button" onClick={handleCreateKey}><KeyRound size={16} />Create key</button>
          </div>
          {createdKey && (
            <div className="copy-secret">
              <span>New key</span>
              <strong>{createdKey}</strong>
              <button className="icon-button" onClick={() => copy(createdKey)} aria-label="Copy API key"><Copy size={16} /></button>
            </div>
          )}
          <div className="api-key-list">
            {keys.map((key) => (
              <div className="api-key-row" key={key.id}>
                <div><strong>{key.name}</strong><span>{key.key_prefix}...</span></div>
                <div><span>Requests</span><strong>{key.request_count}</strong></div>
                <button className="secondary-button" onClick={() => handleRotateKey(key.id)}><RotateCcw size={15} />Rotate</button>
              </div>
            ))}
            {!keys.length && <div className="empty-state slim">{loading ? "Loading keys..." : "No client API keys yet."}</div>}
          </div>
        </div>

        <div className="insight-panel">
          <div className="section-header">
            <div><p className="eyebrow">Volume and outcome</p><h3>Usage</h3></div>
            <RadioTower size={22} />
          </div>
          <div className="developer-metrics">
            <div><span>Total requests</span><strong>{usage?.total_requests ?? 0}</strong></div>
            <div><span>This month</span><strong>{usage?.requests_this_month ?? 0}</strong></div>
            <div><span>Blocked</span><strong>{usage?.blocked ?? 0}</strong></div>
            <div><span>Challenged</span><strong>{usage?.challenged ?? 0}</strong></div>
          </div>
        </div>
      </section>

      <section className="developer-grid">
        <div className="insight-panel">
          <div className="section-header">
            <div><p className="eyebrow">Request</p><h3>Risk Score API</h3></div>
            <button className="secondary-button" onClick={() => copy(curlExample)}><Copy size={15} />Copy curl</button>
          </div>
          <pre className="code-panel">{curlExample}</pre>
        </div>
        <div className="insight-panel">
          <div className="section-header">
            <div><p className="eyebrow">Response</p><h3>Decision Output</h3></div>
          </div>
          <pre className="code-panel">{JSON.stringify(sampleResponse, null, 2)}</pre>
        </div>
      </section>

      <section className="insight-panel">
        <div className="section-header">
          <div><p className="eyebrow">Real-time operations</p><h3>Webhook Alerting</h3></div>
          <Webhook size={22} />
        </div>
        <div className="api-inline-form webhook-form">
          <input value={destinationName} onChange={(event) => setDestinationName(event.target.value)} />
          <input value={destinationTarget} onChange={(event) => setDestinationTarget(event.target.value)} placeholder="https://client.example.com/fraud-webhook" />
          <button className="primary-button" disabled={!destinationTarget} onClick={handleCreateDestination}>Add webhook</button>
        </div>
        <div className="api-key-list">
          {destinations.map((destination) => (
            <div className="api-key-row" key={destination.id}>
              <div><strong>{destination.name}</strong><span>{destination.target}</span></div>
              <div><span>Channel</span><strong>{destination.channel}</strong></div>
              <div><span>Min risk</span><strong>{destination.minimum_risk}</strong></div>
            </div>
          ))}
          {!destinations.length && <div className="empty-state slim">No alert destinations configured.</div>}
        </div>
      </section>

      {message && <div className="form-success">{message}</div>}
    </div>
  );
}
