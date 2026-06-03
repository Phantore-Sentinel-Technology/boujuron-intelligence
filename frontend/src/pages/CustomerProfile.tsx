import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AlertTriangle, ArrowLeft, History, MapPin, MonitorSmartphone, Network, ShieldAlert, TrendingUp } from "lucide-react";
import type { UserRiskProfile } from "../types";
import { getUserRiskProfile } from "../services/api";
import { RiskBadge } from "../components/RiskBadge";
import { ScoreBreakdown } from "../components/ScoreBreakdown";

export function CustomerProfile() {
  const { userId = "" } = useParams();
  const [profile, setProfile] = useState<UserRiskProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getUserRiskProfile(userId)
      .then(setProfile)
      .finally(() => setLoading(false));
  }, [userId]);

  const trend = useMemo(() => {
    if (!profile) return "Stable";
    if (profile.risk_trend === "up") return "Rising";
    if (profile.risk_trend === "down") return "Cooling";
    return "Stable";
  }, [profile]);

  if (loading) return <div className="empty-state">Loading user risk profile...</div>;
  if (!profile) return <div className="empty-state">No profile found for {userId}.</div>;

  return (
    <div className="profile-page">
      <Link className="back-link" to="/users"><ArrowLeft size={16} /> User Intelligence</Link>

      <section className="profile-hero">
        <div>
          <p className="eyebrow">Customer investigation</p>
          <h2>{profile.user_id}</h2>
          <span className={`trend ${profile.risk_trend}`}>{trend} risk trend</span>
        </div>
        <div className="profile-risk">
          <RiskBadge level={profile.risk_level} />
          <strong>{profile.current_risk}</strong>
          <span>current risk</span>
        </div>
      </section>

      <div className="profile-grid">
        <section className="insight-panel profile-card">
          <div className="section-header compact">
            <div>
              <p className="eyebrow">Identity signals</p>
              <h3>Devices & Locations</h3>
            </div>
            <MonitorSmartphone size={20} />
          </div>
          <SignalList title="Known Devices" items={profile.known_devices} empty="No repeated devices yet" />
          <SignalList title="New Devices" items={profile.new_devices} empty="No new device signals" alert />
          <SignalList title="Known Locations" items={profile.known_locations} empty="No repeated locations yet" />
          <div className="signal-row alert"><MapPin size={16} /> Current Location <strong>{profile.current_location || "Unknown"}</strong></div>
        </section>

        <section className="insight-panel profile-card">
          <div className="section-header compact">
            <div>
              <p className="eyebrow">Behavioral profile</p>
              <h3>Normal Pattern</h3>
            </div>
            <History size={20} />
          </div>
          <div className="profile-facts">
            {Object.entries(profile.behavioral_profile).map(([label, value]) => (
              <div key={label}>
                <span>{label}</span>
                <strong>{value}</strong>
              </div>
            ))}
          </div>
        </section>

        <section className="insight-panel profile-card">
          <div className="section-header compact">
            <div>
              <p className="eyebrow">Network history</p>
              <h3>Observed IPs</h3>
            </div>
            <Network size={20} />
          </div>
          <div className="chip-list">
            {profile.ip_history.map((ip) => <span key={ip}>{ip}</span>)}
            {profile.ip_history.length === 0 && <p className="empty-state slim">No IP history yet.</p>}
          </div>
        </section>

        <section className="insight-panel profile-card breakdown-card">
          <ScoreBreakdown items={profile.score_breakdown} total={profile.current_risk} />
        </section>
      </div>

      <div className="profile-grid wide">
        <section className="insight-panel profile-card">
          <div className="section-header compact">
            <div>
              <p className="eyebrow">Behavior anomalies</p>
              <h3>Deviation Highlights</h3>
            </div>
            <AlertTriangle size={20} />
          </div>
          <div className="anomaly-list">
            {profile.behavior_anomalies.map((item) => (
              <div key={`${item.label}-${item.detail}`} className={`anomaly-item ${item.severity.toLowerCase()}`}>
                <strong>{item.label}</strong>
                <span>{item.detail}</span>
              </div>
            ))}
            {profile.behavior_anomalies.length === 0 && <div className="empty-state slim">No major behavioral deviations detected.</div>}
          </div>
        </section>

        <section className="insight-panel profile-card">
          <div className="section-header compact">
            <div>
              <p className="eyebrow">Risk timeline</p>
              <h3>Score Trend</h3>
            </div>
            <TrendingUp size={20} />
          </div>
          <div className="risk-timeline">
            {profile.risk_timeline.map((point) => (
              <div key={`${point.timestamp}-${point.score}`} className="risk-point">
                <time>{point.timestamp.slice(0, 10)}</time>
                <div>
                  <i style={{ height: `${Math.max(point.score, 8)}%` }} />
                </div>
                <strong>{point.score}</strong>
                <RiskBadge level={point.level} />
              </div>
            ))}
            {profile.risk_timeline.length === 0 && <div className="empty-state slim">No risk history yet.</div>}
          </div>
        </section>
      </div>

      <div className="profile-grid wide">
        <section className="insight-panel profile-card">
          <div className="section-header compact">
            <div>
              <p className="eyebrow">Recent events</p>
              <h3>Activity Timeline</h3>
            </div>
          </div>
          <div className="timeline-list">
            {profile.recent_events.map((event) => (
              <div key={`${event.timestamp}-${event.ip}`} className="timeline-item">
                <ShieldAlert size={16} />
                <div>
                  <strong>{event.event_type}</strong>
                  <span>{event.device_type} / {event.location || "Unknown"} / {event.network || "NORMAL"}</span>
                </div>
                <time>{event.timestamp}</time>
              </div>
            ))}
          </div>
        </section>

        <section className="insight-panel profile-card">
          <div className="section-header compact">
            <div>
              <p className="eyebrow">Previous investigations</p>
              <h3>Risk Decisions</h3>
            </div>
          </div>
          <div className="timeline-list">
            {profile.previous_investigations.map((alert) => (
              <div key={`${alert.timestamp}-${alert.risk_score}`} className="timeline-item">
                <RiskBadge level={alert.risk_level} />
                <div>
                  <strong>{alert.risk_score}</strong>
                  <span>{alert.reason}</span>
                </div>
                <time>{alert.timestamp}</time>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function SignalList({ title, items, empty, alert }: { title: string; items: string[]; empty: string; alert?: boolean }) {
  return (
    <div className="signal-group">
      <span>{title}</span>
      {items.map((item) => <div key={item} className={`signal-row ${alert ? "alert" : ""}`}>{item}</div>)}
      {items.length === 0 && <div className="signal-row muted">{empty}</div>}
    </div>
  );
}
