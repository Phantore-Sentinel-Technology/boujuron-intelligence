import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { AlertTriangle, ArrowLeft, History, KeyRound, MapPin, MonitorSmartphone, Network, ShieldAlert, ShieldCheck, ShieldX, TrendingUp } from "lucide-react";
import type { UserRiskProfile } from "../types";
import { getUserRiskProfile, updateDeviceTrust } from "../services/api";
import { RiskBadge } from "../components/RiskBadge";
import { ScoreBreakdown } from "../components/ScoreBreakdown";

export function CustomerProfile() {
  const { userId = "" } = useParams();
  const [profile, setProfile] = useState<UserRiskProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [updatingDevice, setUpdatingDevice] = useState<string | null>(null);

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

  async function setDeviceStatus(fingerprint: string, status: "TRUSTED" | "BLOCKED") {
    setUpdatingDevice(fingerprint);
    try {
      const updated = await updateDeviceTrust(userId, fingerprint, status);
      setProfile((current) => current ? {
        ...current,
        device_inventory: current.device_inventory.map((device) =>
          device.fingerprint === fingerprint ? updated : device
        )
      } : current);
    } finally {
      setUpdatingDevice(null);
    }
  }

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
              <p className="eyebrow">Device fingerprinting</p>
              <h3>Device Trust Inventory</h3>
            </div>
            <MonitorSmartphone size={20} />
          </div>
          <div className="device-inventory">
            {profile.device_inventory.map((device) => (
              <article className={`device-record ${device.status.toLowerCase()}`} key={device.fingerprint}>
                <div className="device-record-heading">
                  <div>
                    <strong>{device.label}</strong>
                    <span>{device.fingerprint.slice(0, 16)}...</span>
                  </div>
                  <span className={`device-status ${device.status.toLowerCase()}`}>{device.status}</span>
                </div>
                <div className="device-record-facts">
                  <span>Trust <strong>{device.trust_score}/100</strong></span>
                  <span>Events <strong>{device.event_count}</strong></span>
                  <span>Last location <strong>{device.last_location || "Unknown"}</strong></span>
                  <span>Last IP <strong>{device.last_ip || "Unknown"}</strong></span>
                </div>
                {device.integrity_flags.length > 0 && (
                  <div className="integrity-flags">
                    {device.integrity_flags.map((flag) => <span key={flag}>{flag.replaceAll("_", " ")}</span>)}
                  </div>
                )}
                <div className="device-actions">
                  <button
                    className="secondary-button compact"
                    disabled={updatingDevice === device.fingerprint || device.status === "TRUSTED"}
                    onClick={() => setDeviceStatus(device.fingerprint, "TRUSTED")}
                    type="button"
                  >
                    <ShieldCheck size={15} /> Trust
                  </button>
                  <button
                    className="danger-button compact"
                    disabled={updatingDevice === device.fingerprint || device.status === "BLOCKED"}
                    onClick={() => setDeviceStatus(device.fingerprint, "BLOCKED")}
                    type="button"
                  >
                    <ShieldX size={15} /> Block
                  </button>
                </div>
              </article>
            ))}
            {profile.device_inventory.length === 0 && <div className="empty-state slim">No device fingerprints captured yet.</div>}
          </div>
        </section>

        <section className="insight-panel profile-card">
          <div className="section-header compact">
            <div>
              <p className="eyebrow">Account takeover defense</p>
              <h3>Security State</h3>
            </div>
            <KeyRound size={20} />
          </div>
          {profile.account_security ? (
            <>
              <div className="ato-summary">
                <div>
                  <span>ATO risk</span>
                  <strong>{profile.account_security.takeover_risk}</strong>
                </div>
                <RiskBadge level={profile.account_security.takeover_level} />
                <p>{profile.account_security.recommendation.replaceAll("_", " ")}</p>
              </div>
              <div className="profile-facts security-facts">
                <div><span>Recent failed logins</span><strong>{profile.account_security.recent_failed_logins}</strong></div>
                <div><span>Last successful login</span><strong>{profile.account_security.last_successful_login_at || "Not observed"}</strong></div>
                <div><span>Password changed</span><strong>{profile.account_security.password_changed_at || "No recent change"}</strong></div>
                <div><span>SIM changed</span><strong>{profile.account_security.sim_changed_at || "No recent change"}</strong></div>
              </div>
              <div className="anomaly-list security-indicators">
                {profile.account_security.indicators.map((indicator) => (
                  <div className="anomaly-item critical" key={indicator}>
                    <strong>{indicator}</strong>
                  </div>
                ))}
                {profile.account_security.indicators.length === 0 && <div className="empty-state slim">No takeover indicators active.</div>}
              </div>
            </>
          ) : <div className="empty-state slim">No authentication security activity captured yet.</div>}
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
