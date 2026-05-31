import { motion } from "framer-motion";
import type { FraudAlert } from "../types";
import { RiskBadge } from "./RiskBadge";

export function LiveActivityFeed({ alerts }: { alerts: FraudAlert[] }) {
  return (
    <section className="feed-section">
      <div className="section-header compact">
        <div>
          <p className="eyebrow">Live stream</p>
          <h2>Activity Feed</h2>
        </div>
      </div>
      <div className="feed-list">
        {alerts.slice(0, 8).map((alert, index) => (
          <motion.div
            className="feed-item"
            key={`${alert.user_id}-${alert.timestamp}-${index}`}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.03 }}
          >
            <span>{alert.timestamp?.slice(11, 16) || "--:--"}</span>
            <RiskBadge level={alert.risk_level} />
            <strong>{alert.user_id}</strong>
          </motion.div>
        ))}
        {alerts.length === 0 && <div className="empty-state slim">Awaiting live fraud events.</div>}
      </div>
    </section>
  );
}
