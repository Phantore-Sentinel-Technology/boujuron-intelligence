import axios from "axios";
import { FormEvent, useEffect, useState } from "react";
import { Activity, BellRing, Building2, Code2, Copy, KeyRound, Plus, RefreshCw, ShieldCheck, SlidersHorizontal, Trash2 } from "lucide-react";
import type { AlertDestination, ApiUsage, BehaviorEvaluation, BehaviorSettings, ClientApiKey, ConsortiumSettings, DecisionRule, Invoice, InviteToken, Organization, RuleCondition, RuleField, UserRole } from "../types";
import {
  createClientApiKey,
  createDecisionRule,
  createAlertDestination,
  createInvite,
  createOrganization,
  deleteDecisionRule,
  deleteAlertDestination,
  getBehaviorEvaluation,
  getBehaviorSettings,
  getClientApiKeys,
  getCurrentOrganization,
  getDecisionRules,
  getAlertDestinations,
  getConsortiumSettings,
  getInvoices,
  getPortalUsage,
  rotateClientApiKey,
  revokeClientApiKey,
  updateBehaviorSettings,
  updateConsortiumSettings
} from "../services/api";
import { useAuth } from "../context/AuthContext";

const thresholds = [
  ["LOW", "0-39", "Allow event"],
  ["MEDIUM", "40-69", "Step-up verification"],
  ["HIGH", "70-89", "Block and review"],
  ["CRITICAL", "90-100", "Freeze and escalate"]
];

const inviteRoles: UserRole[] = ["Read-Only Auditor", "Fraud Analyst", "Investigator", "Admin"];
const ruleFields: RuleField[] = ["amount", "risk_score", "risk_level", "event_type", "location", "network", "device_type", "is_new_device", "is_rooted", "is_emulator", "browser_tampering", "sim_swap_detected", "failed_login_count"];
const ruleOperators: RuleCondition["operator"][] = ["EQ", "NEQ", "GT", "GTE", "LT", "LTE", "IN", "CONTAINS"];

export function Settings() {
  const { user } = useAuth();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<UserRole>("Read-Only Auditor");
  const [expiresInHours, setExpiresInHours] = useState(24);
  const [createdInvite, setCreatedInvite] = useState<InviteToken | null>(null);
  const [message, setMessage] = useState("");
  const [inviteError, setInviteError] = useState("");
  const [loadError, setLoadError] = useState("");
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
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [tenantName, setTenantName] = useState("");
  const [tenantAdminEmail, setTenantAdminEmail] = useState("");
  const [tenantMessage, setTenantMessage] = useState("");
  const [rules, setRules] = useState<DecisionRule[]>([]);
  const [ruleName, setRuleName] = useState("");
  const [ruleAction, setRuleAction] = useState<DecisionRule["action"]>("BLOCK");
  const [ruleScore, setRuleScore] = useState(20);
  const [rulePriority, setRulePriority] = useState(100);
  const [ruleConditions, setRuleConditions] = useState<RuleCondition[]>([{ field: "amount", operator: "GT", value: 1000000 }]);
  const [ruleMessage, setRuleMessage] = useState("");
  const [savingRule, setSavingRule] = useState(false);
  const [usage, setUsage] = useState<ApiUsage | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [destinations, setDestinations] = useState<AlertDestination[]>([]);
  const [destinationName, setDestinationName] = useState("");
  const [destinationChannel, setDestinationChannel] = useState<AlertDestination["channel"]>("WEBHOOK");
  const [destinationTarget, setDestinationTarget] = useState("");
  const [consortium, setConsortium] = useState<ConsortiumSettings | null>(null);
  const isAdmin = user?.role === "Admin";

  useEffect(() => {
    let mounted = true;
    const failures: string[] = [];

    function loadSetting<T>(name: string, request: Promise<T>, apply: (value: T) => void) {
      return request
        .then((value) => {
          if (mounted) apply(value);
        })
        .catch(() => {
          failures.push(name);
        });
    }

    setLoadError("");

    Promise.all([
      loadSetting("API keys", isAdmin ? getClientApiKeys() : Promise.resolve([]), setApiKeys),
      loadSetting("behavioral baselines", getBehaviorSettings(), setBehaviorSettings),
      loadSetting("adaptive learning health", getBehaviorEvaluation(), setEvaluation),
      loadSetting("organization", getCurrentOrganization(), setOrganization),
      loadSetting("decision rules", getDecisionRules(), setRules),
      loadSetting("usage", getPortalUsage(), setUsage),
      loadSetting("invoices", getInvoices(), setInvoices),
      loadSetting("alert destinations", getAlertDestinations(), setDestinations),
      loadSetting("fraud consortium", getConsortiumSettings(), setConsortium)
    ]).finally(() => {
      if (!mounted) return;
      if (failures.length > 0) {
        setLoadError(`Could not load: ${failures.join(", ")}. The other settings remain available.`);
      }
    });

    return () => {
      mounted = false;
    };
  }, [isAdmin]);

  async function onCreateInvite(event: FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setMessage("");
    setInviteError("");
    try {
      const invite = await createInvite(email, role, expiresInHours);
      setCreatedInvite(invite);
      setEmail("");
      setMessage("Invite generated successfully.");
    } catch (error) {
      setInviteError(getApiErrorMessage(error, "Could not generate invite. Confirm the email and your Admin access."));
    } finally {
      setSubmitting(false);
    }
  }

  async function copyInvite(value: string) {
    await navigator.clipboard.writeText(value);
    setInviteError("");
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

  async function rotateApiKey(keyId: number) {
    const rotated = await rotateClientApiKey(keyId);
    setApiKeys((current) => [rotated, ...current.map((item) => item.id === keyId ? { ...item, active: false } : item)]);
    setCreatedApiKey(rotated);
    setApiKeyMessage("API key rotated. Copy the new key now.");
  }

  async function onCreateDestination(event: FormEvent) {
    event.preventDefault();
    const created = await createAlertDestination({ name: destinationName, channel: destinationChannel, target: destinationTarget, minimum_risk: "HIGH", enabled: true });
    setDestinations((current) => [...current, created]);
    setDestinationName(""); setDestinationTarget("");
  }

  async function removeDestination(id: number) {
    await deleteAlertDestination(id);
    setDestinations((current) => current.filter((item) => item.id !== id));
  }

  async function toggleConsortium() {
    if (!consortium) return;
    const updated = await updateConsortiumSettings({ ...consortium, enabled: !consortium.enabled });
    setConsortium(updated);
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

  async function onCreateTenant(event: FormEvent) {
    event.preventDefault();
    setTenantMessage("");
    try {
      const created = await createOrganization(tenantName, tenantAdminEmail);
      setTenantMessage(`Tenant created. Admin invite: ${created.admin_invite_url}`);
      setTenantName("");
      setTenantAdminEmail("");
    } catch {
      setTenantMessage("Could not create tenant. Confirm the name is unique and you have Admin access.");
    }
  }

  function updateRuleCondition(index: number, changes: Partial<RuleCondition>) {
    setRuleConditions((current) => current.map((condition, conditionIndex) =>
      conditionIndex === index ? { ...condition, ...changes } : condition
    ));
  }

  async function onCreateRule(event: FormEvent) {
    event.preventDefault();
    setSavingRule(true);
    setRuleMessage("");
    try {
      const created = await createDecisionRule({
        name: ruleName,
        conditions: ruleConditions.map((condition) => ({
          ...condition,
          value: ["GT", "GTE", "LT", "LTE"].includes(condition.operator) ? Number(condition.value) : condition.value
        })),
        action: ruleAction,
        score_adjustment: ruleScore,
        priority: rulePriority,
        enabled: true
      });
      setRules((current) => [...current, created].sort((left, right) => left.priority - right.priority));
      setRuleName("");
      setRuleMessage("Decision rule activated.");
    } catch {
      setRuleMessage("Could not create rule. Check the conditions and rule name.");
    } finally {
      setSavingRule(false);
    }
  }

  async function removeRule(ruleId: number) {
    await deleteDecisionRule(ruleId);
    setRules((current) => current.filter((rule) => rule.id !== ruleId));
    setRuleMessage("Decision rule deleted.");
  }

  return (
    <div className="page-grid">
      {loadError && <div className="form-error settings-load-error">{loadError}</div>}
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
            <p className="eyebrow">Tenant isolation</p>
            <h2>{organization?.name || "Organization"}</h2>
          </div>
          <Building2 size={22} />
        </div>
        <p className="settings-copy">Users, API keys, events, alerts, cases, exports, analytics, rules, and live notifications are isolated by organization.</p>
        {isAdmin && organization?.slug === "boujuron" && (
          <form className="tenant-form" onSubmit={onCreateTenant}>
            <label><span>New tenant name</span><input value={tenantName} onChange={(event) => setTenantName(event.target.value)} placeholder="Acme Fintech" required /></label>
            <label><span>Tenant admin email</span><input value={tenantAdminEmail} onChange={(event) => setTenantAdminEmail(event.target.value)} type="email" placeholder="admin@acme.com" required /></label>
            <button className="primary-button"><Building2 size={17} />Provision tenant</button>
          </form>
        )}
        {tenantMessage && <p className="form-success tenant-message">{tenantMessage}</p>}
      </section>

      <section className="insight-panel access-panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">No-code enforcement</p>
            <h2>Decision Rules</h2>
          </div>
          <SlidersHorizontal size={22} />
        </div>
        {isAdmin && (
          <form className="rule-builder" onSubmit={onCreateRule}>
            <div className="rule-meta-grid">
              <label><span>Rule name</span><input value={ruleName} onChange={(event) => setRuleName(event.target.value)} placeholder="Block large new-device transfers" required /></label>
              <label><span>Action</span><select value={ruleAction} onChange={(event) => setRuleAction(event.target.value as DecisionRule["action"])}><option>ALLOW</option><option>CHALLENGE</option><option>BLOCK</option></select></label>
              <NumberSetting label="Score adjustment" value={ruleScore} onChange={setRuleScore} disabled={false} />
              <NumberSetting label="Priority" value={rulePriority} onChange={setRulePriority} disabled={false} />
            </div>
            <div className="rule-condition-list">
              {ruleConditions.map((condition, index) => (
                <div className="rule-condition" key={`${condition.field}-${index}`}>
                  <select value={condition.field} onChange={(event) => updateRuleCondition(index, { field: event.target.value as RuleField })}>
                    {ruleFields.map((field) => <option key={field} value={field}>{field.replaceAll("_", " ")}</option>)}
                  </select>
                  <select value={condition.operator} onChange={(event) => updateRuleCondition(index, { operator: event.target.value as RuleCondition["operator"] })}>
                    {ruleOperators.map((operator) => <option key={operator}>{operator}</option>)}
                  </select>
                  <input value={String(condition.value)} onChange={(event) => updateRuleCondition(index, { value: event.target.value })} aria-label={`Condition ${index + 1} value`} />
                  <button type="button" className="icon-button" title="Remove condition" disabled={ruleConditions.length === 1} onClick={() => setRuleConditions((current) => current.filter((_, itemIndex) => itemIndex !== index))}><Trash2 size={15} /></button>
                </div>
              ))}
            </div>
            <div className="rule-builder-actions">
              <button type="button" className="small-button" onClick={() => setRuleConditions((current) => [...current, { field: "is_new_device", operator: "EQ", value: true }])}><Plus size={15} />Add AND condition</button>
              <button className="primary-button" disabled={savingRule}>{savingRule ? "Activating..." : "Activate rule"}</button>
            </div>
          </form>
        )}
        {ruleMessage && <p className="form-success">{ruleMessage}</p>}
        <div className="rule-list">
          {rules.map((rule) => (
            <div className="rule-row" key={rule.id}>
              <div><strong>{rule.name}</strong><span>{rule.conditions.map((condition) => `${condition.field} ${condition.operator} ${String(condition.value)}`).join(" AND ")}</span></div>
              <span className={`rule-action ${rule.action.toLowerCase()}`}>{rule.action}</span>
              {isAdmin && <button className="icon-button" title="Delete rule" onClick={() => removeRule(rule.id)}><Trash2 size={15} /></button>}
            </div>
          ))}
          {rules.length === 0 && <div className="empty-state slim">No organization rules configured.</div>}
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
            {inviteError && <p className="form-error">{inviteError}</p>}

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

            <p className="settings-copy">The complete invitation audit trail is available on the History page.</p>
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
                  <div className="inline-actions">
                    <span>{apiKey.request_count} requests</span>
                    <button className="icon-button" title="Rotate key" disabled={!apiKey.active} onClick={() => rotateApiKey(apiKey.id)}><RefreshCw size={15} /></button>
                    <button className="icon-button" title="Revoke key" disabled={!apiKey.active} onClick={() => revokeApiKey(apiKey.id)}><Trash2 size={15} /></button>
                  </div>
                </div>
              ))}
              {apiKeys.length === 0 && <div className="empty-state slim">No client API keys yet.</div>}
            </div>
          </>
        )}
      </section>

      <section className="insight-panel access-panel">
        <div className="section-header"><div><p className="eyebrow">Customer portal</p><h2>Usage & Billing</h2></div><Activity size={22} /></div>
        {usage && <div className="evaluation-grid">
          <EvaluationMetric label="Total requests" value={usage.total_requests} />
          <EvaluationMetric label="This month" value={usage.requests_this_month} />
          <EvaluationMetric label="Blocked" value={usage.blocked} />
          <EvaluationMetric label="Challenged" value={usage.challenged} />
          <EvaluationMetric label="Allowed" value={usage.allowed} />
        </div>}
        <div className="invoice-list">
          {invoices.map((invoice) => <div className="invoice-row" key={invoice.id}><strong>{invoice.invoice_number}</strong><span>{invoice.period}</span><span>{invoice.currency} {invoice.amount.toFixed(2)}</span><span>{invoice.status}</span></div>)}
        </div>
      </section>

      <section className="insight-panel access-panel">
        <div className="section-header"><div><p className="eyebrow">Real-time operations</p><h2>Alert Destinations</h2></div><BellRing size={22} /></div>
        {isAdmin && <form className="destination-form" onSubmit={onCreateDestination}>
          <input value={destinationName} onChange={(event) => setDestinationName(event.target.value)} placeholder="Fraud operations" required />
          <select value={destinationChannel} onChange={(event) => setDestinationChannel(event.target.value as AlertDestination["channel"])}><option>WEBHOOK</option><option>SLACK</option><option>TEAMS</option><option>EMAIL</option></select>
          <input value={destinationTarget} onChange={(event) => setDestinationTarget(event.target.value)} placeholder="Webhook URL or email" required />
          <button className="primary-button">Add destination</button>
        </form>}
        <div className="invite-list">
          {destinations.map((item) => <div className="invite-row" key={item.id}><div><strong>{item.name}</strong><span>{item.channel} · HIGH+ · {item.last_status || "Not sent yet"}</span></div><span className="invite-status active">{item.enabled ? "Active" : "Paused"}</span>{isAdmin && <button className="icon-button" title="Delete destination" onClick={() => removeDestination(item.id)}><Trash2 size={15} /></button>}</div>)}
          {!destinations.length && <div className="empty-state slim">No outbound alert destinations configured.</div>}
        </div>
      </section>

      <section className="insight-panel access-panel">
        <div className="section-header"><div><p className="eyebrow">Privacy-preserving intelligence</p><h2>Fraud Consortium</h2></div><ShieldCheck size={22} /></div>
        <p className="settings-copy">Shares salted hashes and aggregate fraud counts only. Raw customer identifiers never leave the tenant boundary.</p>
        {consortium && <div className="consortium-control"><div><strong>{consortium.enabled ? "Consortium enabled" : "Consortium disabled"}</strong><span>Device and IP reputation across opted-in organizations</span></div>{isAdmin && <button className="primary-button" onClick={toggleConsortium}>{consortium.enabled ? "Disable" : "Enable"}</button>}</div>}
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

function getApiErrorMessage(error: unknown, fallback: string) {
  if (!axios.isAxiosError(error)) return fallback;
  const detail = error.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) return detail;
  return fallback;
}
