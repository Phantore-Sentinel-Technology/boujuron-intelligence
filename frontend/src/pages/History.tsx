import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Clock3, Filter, History as HistoryIcon, KeyRound, Search } from "lucide-react";
import type { AuditLog, IntelligenceActivity, InvestigationFeedItem, InviteToken } from "../types";
import { getAuditLogs, getIntelligenceActivity, getInvites } from "../services/api";
import { RiskBadge } from "../components/RiskBadge";
import { useAuth } from "../context/AuthContext";

export function History() {
  const { user } = useAuth();
  const [activity, setActivity] = useState<IntelligenceActivity>({ notifications: [], feed: [] });
  const [invites, setInvites] = useState<InviteToken[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [query, setQuery] = useState("");
  const [eventType, setEventType] = useState("ALL");
  const [loading, setLoading] = useState(true);
  const isAdmin = user?.role === "Admin";

  useEffect(() => {
    let mounted = true;
    const load = () => {
      Promise.allSettled([
        getIntelligenceActivity(200),
        getAuditLogs(200),
        isAdmin ? getInvites() : Promise.resolve([] as InviteToken[])
      ])
        .then(([activityResult, auditResult, inviteResult]) => {
          if (!mounted) return;
          if (activityResult.status === "fulfilled") setActivity(activityResult.value);
          if (auditResult.status === "fulfilled") setAuditLogs(auditResult.value);
          if (inviteResult.status === "fulfilled") setInvites(inviteResult.value);
        })
        .finally(() => mounted && setLoading(false));
    };
    load();
    const timer = window.setInterval(load, 12000);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, [isAdmin]);

  const eventTypes = useMemo(() => {
    const values = [
      ...activity.feed.map((item) => item.event_type).filter(Boolean),
      ...auditLogs.map((item) => item.action_taken).filter(Boolean),
    ];
    return ["ALL", ...Array.from(new Set(values))];
  }, [activity.feed, auditLogs]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return activity.feed.filter((item) => {
      const matchesType = eventType === "ALL" || item.event_type === eventType;
      const content = `${item.event_type} ${item.description} ${item.actor} ${item.case_number || ""} ${item.user_id || ""}`.toLowerCase();
      return matchesType && (!needle || content.includes(needle));
    });
  }, [activity.feed, eventType, query]);

  const filteredInvites = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return invites.filter((invite) => {
      const content = `${invite.email} ${invite.role} ${invite.created_by || ""} ${inviteStatus(invite)}`.toLowerCase();
      return !needle || content.includes(needle);
    });
  }, [invites, query]);

  const filteredAuditLogs = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return auditLogs.filter((item) => {
      const matchesType = eventType === "ALL" || item.action_taken === eventType;
      const content = `${item.action_taken} ${item.user_id || ""} ${item.transaction_id || ""} ${item.case_id || ""} ${item.previous_status || ""} ${item.new_status || ""} ${item.analyst_note || ""}`.toLowerCase();
      return matchesType && (!needle || content.includes(needle));
    });
  }, [auditLogs, eventType, query]);

  const totalRecords = filtered.length + filteredInvites.length + filteredAuditLogs.length;

  return (
    <div className="page-grid">
      <section className="case-command history-command">
        <div>
          <p className="eyebrow">Platform audit trail</p>
          <h2>History</h2>
        </div>
        <div className="live-indicator history-count">
          <Clock3 size={18} />
          {totalRecords} records
        </div>
      </section>

      {isAdmin && (
        <section className="insight-panel history-panel">
          <div className="section-header">
            <div>
              <p className="eyebrow">Access history</p>
              <h3>Registration Invitations</h3>
            </div>
            <KeyRound size={20} />
          </div>
          <div className="history-list">
            {filteredInvites.map((invite) => <InviteHistoryItem key={invite.id} invite={invite} />)}
            {!loading && filteredInvites.length === 0 && <div className="empty-state slim">No matching invitation records yet.</div>}
          </div>
        </section>
      )}

      <section className="insight-panel history-panel">
        <div className="section-header">
          <div>
            <p className="eyebrow">Investigation history</p>
            <h3>Everything That Happened</h3>
          </div>
          <div className="table-tools">
            <label className="search-box">
              <Search size={16} />
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search history" />
            </label>
            <label className="filter-select">
              <Filter size={14} />
              <span>Type</span>
              <select value={eventType} onChange={(event) => setEventType(event.target.value)}>
                {eventTypes.map((item) => <option key={item} value={item}>{formatLabel(item)}</option>)}
              </select>
            </label>
          </div>
        </div>

        <div className="history-list">
          {filteredAuditLogs.map((item) => <AuditHistoryItem key={`audit-${item.id}`} item={item} />)}
          {filtered.map((item) => <HistoryItem key={item.id} item={item} />)}
          {loading && <div className="empty-state slim">Loading platform history...</div>}
          {!loading && filtered.length === 0 && filteredAuditLogs.length === 0 && <div className="empty-state slim">No matching history records yet.</div>}
        </div>
      </section>
    </div>
  );
}

function AuditHistoryItem({ item }: { item: AuditLog }) {
  return (
    <article className="history-item audit-history-item">
      <div className="history-icon">
        <HistoryIcon size={17} />
      </div>
      <div>
        <div className="history-title">
          <strong>{formatLabel(item.action_taken)}</strong>
          {item.new_status && <span className="audit-status">{formatLabel(item.new_status)}</span>}
        </div>
        <p>
          {decisionSentence(item)}
          {item.analyst_note ? ` Note: ${item.analyst_note}` : ""}
        </p>
        <span>
          {item.transaction_id ? `Transaction ${item.transaction_id}` : "No transaction ID"}
          {item.case_id ? ` / Case #${item.case_id}` : ""}
          {item.user_id ? ` / ${item.user_id}` : ""}
          {item.previous_status && item.new_status ? ` / ${formatLabel(item.previous_status)} to ${formatLabel(item.new_status)}` : ""}
        </span>
      </div>
      <time>{formatTime(item.created_at)}</time>
    </article>
  );
}

function decisionSentence(item: AuditLog) {
  if (item.action_taken === "REVERSED") return "An analyst reversed the transaction restriction.";
  if (item.action_taken === "CONFIRMED_FRAUD") return "An analyst confirmed this case as fraud.";
  if (item.action_taken === "MARKED_FALSE_POSITIVE") return "An analyst marked this case as a false positive.";
  if (item.action_taken === "TRANSACTION_BLOCKED") return "Boujuron applied a block or PND decision.";
  if (item.action_taken === "TRANSACTION_HELD") return "Boujuron held this transaction for review.";
  if (item.action_taken === "CLOSED") return "An analyst closed this case.";
  if (item.action_taken === "CASE_REVIEWED") return "An analyst moved this case into review.";
  return "Boujuron recorded a platform decision.";
}

function InviteHistoryItem({ invite }: { invite: InviteToken }) {
  const status = inviteStatus(invite);
  return (
    <article className="history-item">
      <div className="history-icon">
        <KeyRound size={17} />
      </div>
      <div>
        <div className="history-title">
          <strong>Registration invite</strong>
          <span className={`invite-status ${status === "Active" ? "active" : "used"}`}>{status}</span>
        </div>
        <p>{invite.email} was invited as {invite.role}.</p>
        <span>Created by {invite.created_by || "Platform Admin"} / expires {formatTime(invite.expires_at)}</span>
      </div>
      <time>{formatTime(invite.created_at)}</time>
    </article>
  );
}

function inviteStatus(invite: InviteToken) {
  if (invite.used_at) return "Used";
  if (new Date(invite.expires_at).getTime() <= Date.now()) return "Expired";
  return "Active";
}

function HistoryItem({ item }: { item: InvestigationFeedItem }) {
  return (
    <article className="history-item">
      <div className="history-icon">
        <HistoryIcon size={17} />
      </div>
      <div>
        <div className="history-title">
          <strong>{formatLabel(item.event_type)}</strong>
          {item.risk_level && <RiskBadge level={item.risk_level} />}
        </div>
        <p>{item.description}</p>
        <span>
          {item.actor}
          {item.case_id && item.case_number && (
            <>
              {" / "}
              <Link to={`/cases/${item.case_id}`}>{item.case_number}</Link>
            </>
          )}
          {item.user_id && ` / ${item.user_id}`}
        </span>
      </div>
      <time>{formatTime(item.created_at)}</time>
    </article>
  );
}

function formatLabel(value: string) {
  return value.replaceAll("_", " ");
}

function formatTime(value: string) {
  return value?.replace("T", " ").slice(0, 19) || "N/A";
}
