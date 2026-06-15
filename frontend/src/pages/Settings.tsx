import { FormEvent, useEffect, useState } from "react";
import { Copy, KeyRound, ShieldCheck } from "lucide-react";
import type { InviteToken, UserRole } from "../types";
import { createInvite, getInvites } from "../services/api";
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
  const isAdmin = user?.role === "Admin";

  useEffect(() => {
    if (!isAdmin) return;
    setLoadingInvites(true);
    getInvites()
      .then(setInvites)
      .catch(() => setMessage("Could not load invite history."))
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
    </div>
  );
}

function formatTime(value: string) {
  return value?.replace("T", " ").slice(0, 19) || "N/A";
}
