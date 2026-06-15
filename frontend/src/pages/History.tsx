import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Clock3, Filter, History as HistoryIcon, Search } from "lucide-react";
import type { IntelligenceActivity, InvestigationFeedItem } from "../types";
import { getIntelligenceActivity } from "../services/api";
import { RiskBadge } from "../components/RiskBadge";

export function History() {
  const [activity, setActivity] = useState<IntelligenceActivity>({ notifications: [], feed: [] });
  const [query, setQuery] = useState("");
  const [eventType, setEventType] = useState("ALL");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const load = () => {
      getIntelligenceActivity(200)
        .then((data) => mounted && setActivity(data))
        .finally(() => mounted && setLoading(false));
    };
    load();
    const timer = window.setInterval(load, 12000);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, []);

  const eventTypes = useMemo(() => {
    const values = activity.feed.map((item) => item.event_type).filter(Boolean);
    return ["ALL", ...Array.from(new Set(values))];
  }, [activity.feed]);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return activity.feed.filter((item) => {
      const matchesType = eventType === "ALL" || item.event_type === eventType;
      const content = `${item.event_type} ${item.description} ${item.actor} ${item.case_number || ""} ${item.user_id || ""}`.toLowerCase();
      return matchesType && (!needle || content.includes(needle));
    });
  }, [activity.feed, eventType, query]);

  return (
    <div className="page-grid">
      <section className="case-command history-command">
        <div>
          <p className="eyebrow">Platform audit trail</p>
          <h2>History</h2>
        </div>
        <div className="live-indicator history-count">
          <Clock3 size={18} />
          {filtered.length} records
        </div>
      </section>

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
          {filtered.map((item) => <HistoryItem key={item.id} item={item} />)}
          {loading && <div className="empty-state slim">Loading platform history...</div>}
          {!loading && filtered.length === 0 && <div className="empty-state slim">No matching history records yet.</div>}
        </div>
      </section>
    </div>
  );
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
