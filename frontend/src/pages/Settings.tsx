const thresholds = [
  ["LOW", "0-39", "Allow event"],
  ["MEDIUM", "40-69", "Step-up verification"],
  ["HIGH", "70-89", "Block and review"],
  ["CRITICAL", "90-100", "Freeze and escalate"]
];

export function Settings() {
  return (
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
  );
}
