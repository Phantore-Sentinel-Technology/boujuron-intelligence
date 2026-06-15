import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { BriefcaseBusiness, Filter, Search } from "lucide-react";
import type { CasePriority, CaseStatus, CaseSummary, RiskLevel } from "../types";
import { getCases } from "../services/api";
import { RiskBadge } from "../components/RiskBadge";

const statuses: Array<"ALL" | CaseStatus> = ["ALL", "NEW", "ASSIGNED", "INVESTIGATING", "ESCALATED", "RESOLVED", "ARCHIVED"];
const priorities: Array<"ALL" | CasePriority> = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"];
const risks: Array<"ALL" | RiskLevel> = ["ALL", "CRITICAL", "HIGH", "MEDIUM", "LOW"];

export function Cases() {
  const [cases, setCases] = useState<CaseSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState<"ALL" | CaseStatus>("ALL");
  const [priority, setPriority] = useState<"ALL" | CasePriority>("ALL");
  const [risk, setRisk] = useState<"ALL" | RiskLevel>("ALL");

  useEffect(() => {
    setLoading(true);
    getCases({
      status: status === "ALL" ? "" : status,
      priority: priority === "ALL" ? "" : priority,
      risk_level: risk === "ALL" ? "" : risk
    })
      .then(setCases)
      .finally(() => setLoading(false));
  }, [status, priority, risk]);

  const filtered = useMemo(() => {
    const needle = query.toLowerCase();
    return cases.filter((item) => {
      return item.case_number.toLowerCase().includes(needle) || item.user_id.toLowerCase().includes(needle) || (item.assigned_to || "").toLowerCase().includes(needle);
    });
  }, [cases, query]);

  const metrics = useMemo(() => ({
    open: cases.filter((item) => !["RESOLVED", "ARCHIVED"].includes(item.status)).length,
    escalated: cases.filter((item) => item.status === "ESCALATED").length,
    resolved: cases.filter((item) => item.status === "RESOLVED").length
  }), [cases]);

  return (
    <div className="page-grid">
      <section className="case-command">
        <div>
          <p className="eyebrow">Investigation operations</p>
          <h2>Case Management</h2>
        </div>
        <div className="case-metrics">
          <span><strong>{metrics.open}</strong> Open</span>
          <span><strong>{metrics.escalated}</strong> Escalated</span>
          <span><strong>{metrics.resolved}</strong> Resolved</span>
        </div>
      </section>

      <section className="table-section case-table-section">
        <div className="section-header">
          <div>
            <p className="eyebrow">Case queue</p>
            <h2>Fraud Investigations</h2>
          </div>
          <div className="table-tools case-tools">
            <label className="search-box">
              <Search size={16} />
              <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search cases" />
            </label>
            <SelectFilter label="Status" value={status} values={statuses} onChange={setStatus} />
            <SelectFilter label="Priority" value={priority} values={priorities} onChange={setPriority} />
            <SelectFilter label="Risk" value={risk} values={risks} onChange={setRisk} />
          </div>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>User</th>
                <th>Risk</th>
                <th>Status</th>
                <th>Priority</th>
                <th>Assigned To</th>
                <th>Feedback</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr key={item.id}>
                  <td><Link className="case-link" to={`/cases/${item.id}`}><BriefcaseBusiness size={15} /> {item.case_number}</Link></td>
                  <td>{item.user_id}</td>
                  <td><RiskBadge level={item.risk_level} /></td>
                  <td><span className={`status-pill ${item.status.toLowerCase()}`}>{formatLabel(item.status)}</span></td>
                  <td><span className={`priority-pill ${item.priority.toLowerCase()}`}>{item.priority}</span></td>
                  <td>{item.assigned_to || "Unassigned"}</td>
                  <td>{item.analyst_feedback ? formatLabel(item.analyst_feedback) : "Pending"}</td>
                  <td>{formatDate(item.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!loading && filtered.length === 0 && <div className="empty-state">No matching cases yet.</div>}
          {loading && <div className="empty-state">Loading case queue...</div>}
        </div>
      </section>
    </div>
  );
}

function SelectFilter<T extends string>({ label, value, values, onChange }: { label: string; value: T; values: T[]; onChange: (value: T) => void }) {
  return (
    <label className="filter-select">
      <Filter size={14} />
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value as T)}>
        {values.map((item) => <option key={item}>{item}</option>)}
      </select>
    </label>
  );
}

function formatLabel(value: string) {
  return value.replaceAll("_", " ");
}

function formatDate(value: string) {
  return value?.replace("T", " ").slice(0, 19) || "N/A";
}
