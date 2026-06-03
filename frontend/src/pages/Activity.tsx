import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Activity as ActivityIcon, Bell, BriefcaseBusiness, RadioTower } from "lucide-react";
import type { IntelligenceActivity } from "../types";
import { getIntelligenceActivity } from "../services/api";
import { RiskBadge } from "../components/RiskBadge";

export function Activity() {
  const [activity, setActivity] = useState<IntelligenceActivity>({ notifications: [], feed: [] });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const load = () => {
      getIntelligenceActivity(50)
        .then((data) => mounted && setActivity(data))
        .finally(() => mounted && setLoading(false));
    };
    load();
    const timer = window.setInterval(load, 8000);
    return () => {
      mounted = false;
      window.clearInterval(timer);
    };
  }, []);

  return (
    <div className="page-grid">
      <section className="case-command">
        <div>
          <p className="eyebrow">Security operations center</p>
          <h2>Live Investigation Feed</h2>
        </div>
        <div className="live-indicator">
          <RadioTower size={18} />
          Live activity
        </div>
      </section>

      <div className="activity-grid">
        <section className="insight-panel profile-card">
          <div className="section-header compact">
            <div>
              <p className="eyebrow">Real-time notifications</p>
              <h3>Operational Alerts</h3>
            </div>
            <Bell size={20} />
          </div>
          <div className="notification-list full">
            {activity.notifications.map((item) => (
              <Link key={item.id} to={item.case_id ? `/cases/${item.case_id}` : "/cases"} className={`notification-item ${item.severity.toLowerCase()}`}>
                <strong>{item.title}</strong>
                <span>{item.message}</span>
                <time>{formatTime(item.created_at)}</time>
              </Link>
            ))}
            {!loading && activity.notifications.length === 0 && <div className="empty-state slim">No notifications yet.</div>}
          </div>
        </section>

        <section className="insight-panel profile-card">
          <div className="section-header compact">
            <div>
              <p className="eyebrow">Investigation stream</p>
              <h3>Case Timeline</h3>
            </div>
            <ActivityIcon size={20} />
          </div>
          <div className="investigation-feed">
            {activity.feed.map((item) => (
              <div key={item.id} className="feed-event">
                <div className="feed-event-icon"><BriefcaseBusiness size={16} /></div>
                <div>
                  <strong>{formatLabel(item.event_type)}</strong>
                  <span>{item.description} by {item.actor}</span>
                  <small>
                    {item.case_id && <Link to={`/cases/${item.case_id}`}>{item.case_number}</Link>}
                    {item.user_id && ` / ${item.user_id}`}
                  </small>
                </div>
                <div className="feed-event-side">
                  {item.risk_level && <RiskBadge level={item.risk_level} />}
                  <time>{formatTime(item.created_at)}</time>
                </div>
              </div>
            ))}
            {loading && <div className="empty-state slim">Loading investigation feed...</div>}
            {!loading && activity.feed.length === 0 && <div className="empty-state slim">No investigation events yet.</div>}
          </div>
        </section>
      </div>
    </div>
  );
}

function formatLabel(value: string) {
  return value.replaceAll("_", " ");
}

function formatTime(value: string) {
  return value?.replace("T", " ").slice(0, 19) || "N/A";
}
