import { FormEvent, useEffect, useState } from "react";
import { Activity, Code2, Copy, KeyRound, ShieldCheck, SlidersHorizontal, Trash2 } from "lucide-react";
import type { BehaviorEvaluation, BehaviorSettings, ClientApiKey, InviteToken, UserRole } from "../types";
import {
  createClientApiKey,
  createInvite,
  getBehaviorEvaluation,
  getBehaviorSettings,
  getClientApiKeys,
  getInvites,
  revokeClientApiKey,
  updateBehaviorSettings
} from "../services/api";
import { useAuth } from "../context/AuthContext";

const thresholds = [
  ["LOW", "0-39", "Allow event"],
  ["MEDIUM", "40-69", "Step-up verification"],
  ["HIGH", "70-89", "Block and review"],
  ["CRITICAL", "90-100", "Freeze and escalate"]
];

const inviteRoles: UserRole[] = ["Read-Only Auditor", "Fraud Analyst", "Investigator", "Admin"];

export function Settings() {
  const { user } = useAuth();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<UserRole>("Read-Only Auditor");
  const [expiresInHours, setExpiresInHours] = useState(24);
  const [invites, setInvites] = useState<InviteToken[]>([]);
  const [createdInvite, setCreatedInvite] = useState<InviteToken | null>(null);
  const [message, setMessage] = useState("");
  const [loadingInvites, setLoadingInvites] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [apiKeyName, setApiKeyName] = useState("");
  const [apiKeys, setApiKeys] = useState<ClientApiKey[]>([]);
  const [createdApiKey, setCreatedApiKey] = useState<ClientApiKey | null>(null);
  const [apiKeyMessage, setApiKeyMessage] = useState("");
  const [creatingApiKey, setCreatingApiKey] = useState(false);
  const [behaviorSettings, setBehaviorSettings] = useState<BehaviorSettings | null>(null);
  const [evaluation, setEvaluation] = useState<BehaviorEvaluation | null>(null);
  const [behaviorMessage, setBehaviorMessage] = useState("");
  const [savingBehavior, setSavingBehavior] = useState(false);
  const isAdmin = user?.role === "Admin";

  useEffect(() => {
    setLoadingInvites(true);
    const adminRequests = isAdmin ? Promise.all([getInvites(), getClientApiKeys()]) : Promise.resolve([[], []] as [InviteToken[], ClientApiKey[]]);
    Promise.all([adminRequests, getBehaviorSettings(), getBehaviorEvaluation()])
      .then(([[inviteData, apiKeyData], settingsData, evaluationData]) => {
        setInvites(inviteData);
        setApiKeys(apiKeyData);
        setBehaviorSettings(settingsData);
        setEvaluation(evaluationData);
      })
      .catch(() => setMessage("Could not load all platform settings."))
      .finally(() => setLoadingInvites(false));
  }, [isAdmin]);

  async function onCreateInvite(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setMessage("");
    try {
      const invite = await createInvite(email, role, expiresInHours);
      setCreatedInvite(invite);
      setInvites((current) => [invite, ...current]);
      setEmail("");
      setMessage("Invite generated successfully.");
    } catch {
      setMessage("Could not generate invite. Admin access is required.");
    } finally {
      setSubmitting(false);
    }
  }

  async function copyInvite(value: string) {
    await navigator.clipboard.writeText(value);
    setMessage("Invite link copied.");
  }

  async function onCreateApiKey(event: FormEvent) {
    event.preventDefault();
    setCreatingApiKey(true);
    setApiKeyMessage("");
    try {
      const apiKey = await createClientApiKey(apiKeyName);
      setCreatedApiKey(apiKey);
      setApiKeys((current) => [apiKey, ...current]);
      setApiKeyName("");
      setApiKeyMessage("API key created. Copy it now; the full key is shown only once.");
    } catch {
      setApiKeyMessage("Could not create API key. Admin access is required.");
    } finally {
      setCreatingApiKey(false);
    }
  }

  async function copyApiKey(value: string) {
    await navigator.clipboard.writeText(value);
    setApiKeyMessage("API key copied.");
  }

  async function revokeApiKey(keyId: number) {
    await revokeClientApiKey(keyId);
    setApiKeys((current) => current.map((item) => item.id === keyId ? { ...item, active: false } : item));
    setApiKeyMessage("API key revoked.");
  }

  function updateBehaviorField<K extends keyof BehaviorSettings>(field: K, value: BehaviorSettings[K]) {
    setBehaviorSettings((current) => current ? { ...current, [field]: value } : current);
  }

  async function onSaveBehavior(event: FormEvent) {
    event.preventDefault();
    if (!behaviorSettings) return;
    setSavingBehavior(true);
    setBehaviorMessage("");
    try {
      const updated = await updateBehaviorSettings({
        amount_spike_multiplier: behaviorSettings.amount_spike_multiplier,
        minimum_amount_delta: behaviorSettings.minimum_amount_delta,
        new_device_points: behaviorSettings.new_device_points,
        new_location_points: behaviorSettings.new_location_points,
        unusual_hour_points: behaviorSettings.unusual_hour_points,
        velocity_window_minutes: behaviorSettings.velocity_window_minutes,
        transaction_velocity_limit: behaviorSettings.transaction_velocity_limit,
        login_velocity_limit: behaviorSettings.login_velocity_limit,
        velocity_points: behaviorSettings.velocity_points,
        minimum_profile_events: behaviorSettings.minimum_profile_events,
        adaptive_learning_enabled: behaviorSettings.adaptive_learning_enabled,
        trusted_learning_max_score: behaviorSettings.trusted_learning_max_score
      });
      setBehaviorSettings(updated);
      setBehaviorMessage("Behavioral intelligence policy saved.");
    } catch {
      setBehaviorMessage("Could not save behavioral policy. Admin access is required.");
    } finally {
      setSavingBehavior(false);
    }
  }

  return (
    <div className="page-grid">
      <section className="insight-panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">Decision policy</p>
            <h2>Risk Thresholds</h2>
          </div>
        </div>
        <div className="threshold-list">
          {thresholds.map(([level, range, action]) => (
            <div key={level}>
              <strong>{level}</strong>
              <span>{range}</span>
              <em>{action}</em>
            </div>
          ))}
        </div>
      </section>

      <section className="insight-panel access-panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">Access control</p>
            <h2>Invite-Only Registration</h2>
          </div>
          <ShieldCheck size={22} />
        </div>

        {!isAdmin && (
          <div className="empty-state slim">Only Admin users can generate registration invites.</div>
        )}

        {isAdmin && (
          <>
            <form className="invite-form" onSubmit={onCreateInvite}>
              <label>
                <span>Email</span>
                <input value={email} onChange={(event) => setEmail(event.target.value)} type="email" placeholder="investor@example.com" required />
              </label>
              <label>
                <span>Role</span>
                <select value={role} onChange={(event) => setRole(event.target.value as UserRole)}>
                  {inviteRoles.map((item) => <option key={item}>{item}</option>)}
                </select>
              </label>
              <label>
                <span>Expires</span>
                <select value={expiresInHours} onChange={(event) => setExpiresInHours(Number(event.target.value))}>
                  <option value={1}>1 hour</option>
                  <option value={6}>6 hours</option>
                  <option value={12}>12 hours</option>
                  <option value={24}>24 hours</option>
                </select>
              </label>
              <button className="primary-button" disabled={submitting}>
                <KeyRound size={17} />
                {submitting ? "Generating..." : "Generate invite"}
              </button>
            </form>

            {message && <p className="form-success">{message}</p>}

            {createdInvite && (
              <div className="invite-result">
                <span>Latest invite link</span>
                <strong>{createdInvite.invite_url}</strong>
                <button className="small-button" onClick={() => copyInvite(createdInvite.invite_url)}>
                  <Copy size={15} />
                  Copy link
                </button>
              </div>
            )}

            <div className="invite-list">
              {invites.map((invite) => (
                <div key={invite.id} className="invite-row">
                  <div>
                    <strong>{invite.email}</strong>
                    <span>{invite.role} / expires {formatTime(invite.expires_at)}</span>
                  </div>
                  <span className={`invite-status ${invite.used_at ? "used" : "active"}`}>{invite.used_at ? "Used" : "Active"}</span>
                  <button className="small-button" onClick={() => copyInvite(invite.invite_url)}>
                    <Copy size={15} />
                    Copy
                  </button>
                </div>
              ))}
              {loadingInvites && <div className="empty-state slim">Loading invites...</div>}
              {!loadingInvites && invites.length === 0 && <div className="empty-state slim">No invites generated yet.</div>}
            </div>
          </>
        )}
      </section>

      <section className="insight-panel access-panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">Developer access</p>
            <h2>Fraud Intelligence API Keys</h2>
          </div>
          <Code2 size={22} />
        </div>

        {!isAdmin && <div className="empty-state slim">Only Admin users can manage client API keys.</div>}

        {isAdmin && (
          <>
            <form className="api-key-form" onSubmit={onCreateApiKey}>
              <label>
                <span>Key name</span>
                <input value={apiKeyName} onChange={(event) => setApiKeyName(event.target.value)} placeholder="Fintech production" minLength={2} required />
              </label>
              <button className="primary-button" disabled={creatingApiKey}>
                <KeyRound size={17} />
                {creatingApiKey ? "Creating..." : "Create API key"}
              </button>
            </form>

            {apiKeyMessage && <p className="form-success">{apiKeyMessage}</p>}

            {createdApiKey?.api_key && (
              <div className="invite-result api-key-result">
                <span>New secret API key</span>
                <strong>{createdApiKey.api_key}</strong>
                <button className="small-button" onClick={() => copyApiKey(createdApiKey.api_key || "")}>
                  <Copy size={15} />
                  Copy key
                </button>
              </div>
            )}

            <div className="invite-list">
              {apiKeys.map((apiKey) => (
                <div key={apiKey.id} className="invite-row">
                  <div>
                    <strong>{apiKey.name}</strong>
                    <span>{apiKey.key_prefix}... / last used {apiKey.last_used_at ? formatTime(apiKey.last_used_at) : "Never"}</span>
                  </div>
                  <span className={`invite-status ${apiKey.active ? "active" : "used"}`}>{apiKey.active ? "Active" : "Revoked"}</span>
                  <button className="small-button" disabled={!apiKey.active} onClick={() => revokeApiKey(apiKey.id)}>
                    <Trash2 size={15} />
                    Revoke
                  </button>
                </div>
              ))}
              {apiKeys.length === 0 && <div className="empty-state slim">No client API keys yet.</div>}
            </div>
          </>
        )}
      </section>

      <section className="insight-panel access-panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">Behavioral intelligence</p>
            <h2>Organization Baselines</h2>
          </div>
          <SlidersHorizontal size={22} />
        </div>

        {behaviorSettings && (
          <form className="behavior-settings-form" onSubmit={onSaveBehavior}>
            <div className="behavior-settings-grid">
              <NumberSetting label="Amount spike multiplier" value={behaviorSettings.amount_spike_multiplier} step={0.5} onChange={(value) => updateBehaviorField("amount_spike_multiplier", value)} disabled={!isAdmin} />
              <NumberSetting label="Minimum amount delta" value={behaviorSettings.minimum_amount_delta} step={10000} onChange={(value) => updateBehaviorField("minimum_amount_delta", value)} disabled={!isAdmin} />
              <NumberSetting label="Profile events required" value={behaviorSettings.minimum_profile_events} onChange={(value) => updateBehaviorField("minimum_profile_events", value)} disabled={!isAdmin} />
              <NumberSetting label="New device points" value={behaviorSettings.new_device_points} onChange={(value) => updateBehaviorField("new_device_points", value)} disabled={!isAdmin} />
              <NumberSetting label="New location points" value={behaviorSettings.new_location_points} onChange={(value) => updateBehaviorField("new_location_points", value)} disabled={!isAdmin} />
              <NumberSetting label="Unusual hour points" value={behaviorSettings.unusual_hour_points} onChange={(value) => updateBehaviorField("unusual_hour_points", value)} disabled={!isAdmin} />
              <NumberSetting label="Velocity window (minutes)" value={behaviorSettings.velocity_window_minutes} onChange={(value) => updateBehaviorField("velocity_window_minutes", value)} disabled={!isAdmin} />
              <NumberSetting label="Transaction limit" value={behaviorSettings.transaction_velocity_limit} onChange={(value) => updateBehaviorField("transaction_velocity_limit", value)} disabled={!isAdmin} />
              <NumberSetting label="Login limit" value={behaviorSettings.login_velocity_limit} onChange={(value) => updateBehaviorField("login_velocity_limit", value)} disabled={!isAdmin} />
              <NumberSetting label="Velocity points" value={behaviorSettings.velocity_points} onChange={(value) => updateBehaviorField("velocity_points", value)} disabled={!isAdmin} />
              <NumberSetting label="Trusted learning max score" value={behaviorSettings.trusted_learning_max_score} onChange={(value) => updateBehaviorField("trusted_learning_max_score", value)} disabled={!isAdmin} />
              <label className="toggle-setting">
                <span>Adaptive learning</span>
                <input type="checkbox" checked={behaviorSettings.adaptive_learning_enabled} onChange={(event) => updateBehaviorField("adaptive_learning_enabled", event.target.checked)} disabled={!isAdmin} />
              </label>
            </div>
            {behaviorMessage && <p className="form-success">{behaviorMessage}</p>}
            {isAdmin && <button className="primary-button behavior-save" disabled={savingBehavior}>{savingBehavior ? "Saving..." : "Save behavioral policy"}</button>}
          </form>
        )}
      </section>

      <section className="insight-panel access-panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">Model evaluation</p>
            <h2>Adaptive Learning Health</h2>
          </div>
          <Activity size={22} />
        </div>
        {evaluation && (
          <div className="evaluation-grid">
            <EvaluationMetric label="Labeled decisions" value={evaluation.labeled_decisions} />
            <EvaluationMetric label="Confirmed fraud" value={evaluation.confirmed_fraud} />
            <EvaluationMetric label="False positives" value={evaluation.false_positives} />
            <EvaluationMetric label="Precision" value={`${evaluation.precision}%`} />
            <EvaluationMetric label="Profiles learning" value={evaluation.profiles_learning} />
            <EvaluationMetric label="Trusted events learned" value={evaluation.trusted_events_learned} />
          </div>
        )}
      </section>
    </div>
  );
}

function NumberSetting({ label, value, step = 1, onChange, disabled }: { label: string; value: number; step?: number; onChange: (value: number) => void; disabled: boolean }) {
  return (
    <label>
      <span>{label}</span>
      <input type="number" value={value} step={step} min={0} onChange={(event) => onChange(Number(event.target.value))} disabled={disabled} />
    </label>
  );
}

function EvaluationMetric({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function formatTime(value: string) {
  return value?.replace("T", " ").slice(0, 19) || "N/A";
}
