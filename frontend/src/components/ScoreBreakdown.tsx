import type { ScoreBreakdownItem } from "../types";

export function ScoreBreakdown({ items, total }: { items: ScoreBreakdownItem[]; total: number }) {
  const safeTotal = Math.max(total, 1);

  return (
    <div className="score-breakdown">
      <div className="section-header compact">
        <div>
          <p className="eyebrow">Explainable score</p>
          <h3>Score Breakdown</h3>
        </div>
        <strong>{total}</strong>
      </div>

      <div className="breakdown-list">
        {items.map((item) => (
          <div key={`${item.label}-${item.points}`} className="breakdown-item">
            <div>
              <strong>+{item.points} {item.label}</strong>
              <span>{item.evidence}</span>
            </div>
            <i style={{ width: `${Math.min((item.points / safeTotal) * 100, 100)}%` }} />
          </div>
        ))}
        {items.length === 0 && <div className="empty-state slim">No explainability signals yet.</div>}
      </div>
    </div>
  );
}
