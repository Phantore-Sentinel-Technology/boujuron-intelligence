import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ArrowLeft, CheckCircle2, Circle, ClipboardCheck, MessageSquarePlus, Save, UserRoundCheck } from "lucide-react";
import type { AnalystFeedback, CaseDecision, CaseDetail as CaseDetailType, CasePriority, CaseStatus } from "../types";
import { addCaseNote, getCase, updateCase } from "../services/api";
import { RiskBadge } from "../components/RiskBadge";
import { ScoreBreakdown } from "../components/ScoreBreakdown";
import { useAuth } from "../context/AuthContext";

const workflow: CaseStatus[] = ["NEW", "ASSIGNED", "INVESTIGATING", "ESCALATED", "RESOLVED", "ARCHIVED"];
const priorities: CasePriority[] = ["LOW", "MEDIUM", "HIGH", "CRITICAL"];
const feedbackOptions: AnalystFeedback[] = ["TRUE_FRAUD", "FALSE_POSITIVE", "NEEDS_REVIEW"];
const decisions: CaseDecision[] = ["ALLOW", "VERIFY", "BLOCK", "FREEZE", "ESCALATE"];

export function CaseDetail() {
  const { caseId = "" } = useParams();
  const { user } = useAuth();
  const [caseRecord, setCaseRecord] = useState<CaseDetailType | null>(null);
  const [assignedTo, setAssignedTo] = useState("");
  const [status, setStatus] = useState<CaseStatus>("NEW");
  const [priority, setPriority] = useState<CasePriority>("LOW");
  const [feedback, setFeedback] = useState<AnalystFeedback | "">("");
  const [decision, setDecision] = useState<CaseDecision | "">("");
  const [potentialLoss, setPotentialLoss] = useState("");
  const [actualLoss, setActualLoss] = useState("");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getCase(caseId).then((data) => {
      setCaseRecord(data);
      syncForm(data);
    });
  }, [caseId]);

  function syncForm(data: CaseDetailType) {
    setAssignedTo(data.assigned_to || "");
    setStatus(data.status);
    setPriority(data.priority);
    setFeedback(data.analyst_feedback || "");
    setDecision(data.decision || "");
    setPotentialLoss(data.potential_loss?.toString() || "");
    setActualLoss(data.actual_loss?.toString() || "");
  }

  async function saveCase(event: FormEvent) {
    event.preventDefault();
    setSaving(true);
    const updated = await updateCase(caseId, {
      assigned_to: assignedTo || null,
      status,
      priority,
      analyst_feedback: feedback || null,
      decision: decision || null,
      potential_loss: potentialLoss ? Number(potentialLoss) : null,
      actual_loss: actualLoss ? Number(actualLoss) : null
    });
    setCaseRecord(updated);
    syncForm(updated);
    setSaving(false);
  }

  async function assignToMe() {
    const updated = await updateCase(caseId, { assigned_to: user?.name || "Current analyst", status: status === "NEW" ? "ASSIGNED" : status });
    setCaseRecord(updated);
    syncForm(updated);
  }

  async function submitNote(event: FormEvent) {
    event.preventDefault();
    if (!note.trim()) return;
    const updated = await addCaseNote(caseId, note);
    setCaseRecord(updated);
    setNote("");
  }

  if (!caseRecord) return <div className="empty-state">Loading case detail...</div>;

  return (
    <div className="case-detail-page">
      <Link className="back-link" to="/cases"><ArrowLeft size={16} /> Cases</Link>

      <section className="case-detail-hero">
        <div>
          <p className="eyebrow">Investigation case</p>
          <h2>{caseRecord.case_number}</h2>
          <span>{caseRecord.user_id}</span>
        </div>
        <div className="case-hero-risk">
          <RiskBadge level={caseRecord.risk_level} />
          <strong>{caseRecord.risk_score}</strong>
          <span>risk score</span>
        </div>
      </section>

      <section className="workflow-strip">
        {workflow.map((step) => {
          const complete = workflow.indexOf(step) <= workflow.indexOf(caseRecord.status);
          return (
            <div key={step} className={complete ? "complete" : ""}>
              {complete ? <CheckCircle2 size={18} /> : <Circle size={18} />}
              <span>{formatLabel(step)}</span>
            </div>
          );
        })}
      </section>

      <div className="case-detail-grid">
        <form className="insight-panel case-control-panel" onSubmit={saveCase}>
          <div className="section-header compact">
            <div>
              <p className="eyebrow">Workflow controls</p>
              <h3>Assignment & Decision</h3>
            </div>
            <button type="button" className="small-button" onClick={assignToMe}><UserRoundCheck size={15} /> Assign me</button>
          </div>

          <label>
            <span>Assigned Analyst</span>
            <input value={assignedTo} onChange={(event) => setAssignedTo(event.target.value)} placeholder="Sarah Analyst" />
          </label>
          <div className="case-form-grid">
            <SelectField label="Status" value={status} values={workflow} onChange={setStatus} />
            <SelectField label="Priority" value={priority} values={priorities} onChange={setPriority} />
            <SelectField label="Decision" value={decision} values={["", ...decisions]} onChange={setDecision} />
            <SelectField label="Analyst Feedback" value={feedback} values={["", ...feedbackOptions]} onChange={setFeedback} />
          </div>
          <div className="case-form-grid">
            <label>
              <span>Potential Loss</span>
              <input value={potentialLoss} onChange={(event) => setPotentialLoss(event.target.value)} type="number" min="0" placeholder="25000" />
            </label>
            <label>
              <span>Actual Loss</span>
              <input value={actualLoss} onChange={(event) => setActualLoss(event.target.value)} type="number" min="0" placeholder="0" />
            </label>
          </div>
          <button className="primary-button" disabled={saving}><Save size={16} /> {saving ? "Saving..." : "Save case"}</button>
        </form>

        <section className="insight-panel case-control-panel">
          <div className="section-header compact">
            <div>
              <p className="eyebrow">Fraud signals</p>
              <h3>Triggered Evidence</h3>
            </div>
            <ClipboardCheck size={20} />
          </div>
          <div className="signal-group">
            {caseRecord.fraud_signals.map((signal) => <div key={signal} className="signal-row alert">{signal}</div>)}
            {caseRecord.fraud_signals.length === 0 && <div className="signal-row muted">No fraud signals recorded.</div>}
          </div>
          <div className="recommended-box">
            <span>AI Recommendation</span>
            <strong>{caseRecord.recommended_action?.replaceAll("_", " ") || "Review"}</strong>
          </div>
        </section>

        <section className="insight-panel case-control-panel">
          <ScoreBreakdown items={caseRecord.score_breakdown} total={caseRecord.risk_score} />
        </section>
      </div>

      <div className="case-detail-grid lower">
        <section className="insight-panel case-control-panel">
          <div className="section-header compact">
            <div>
              <p className="eyebrow">Analyst notes</p>
              <h3>Investigation Notes</h3>
            </div>
          </div>
          <form className="note-form" onSubmit={submitNote}>
            <textarea value={note} onChange={(event) => setNote(event.target.value)} placeholder="Add investigation note..." />
            <button className="primary-button"><MessageSquarePlus size={16} /> Add note</button>
          </form>
          <div className="note-list">
            {caseRecord.notes.map((item) => (
              <div key={item.id} className="note-item">
                <strong>{item.author}</strong>
                <p>{item.note}</p>
                <time>{formatDate(item.created_at)}</time>
              </div>
            ))}
            {caseRecord.notes.length === 0 && <div className="empty-state slim">No notes yet.</div>}
          </div>
        </section>

        <section className="insight-panel case-control-panel">
          <div className="section-header compact">
            <div>
              <p className="eyebrow">Audit trail</p>
              <h3>Investigation Timeline</h3>
            </div>
          </div>
          <div className="timeline-list">
            {caseRecord.timeline.map((item) => (
              <div key={item.id} className="timeline-item">
                <ClipboardCheck size={16} />
                <div>
                  <strong>{formatLabel(item.event_type)}</strong>
                  <span>{item.description} by {item.actor}</span>
                </div>
                <time>{formatDate(item.created_at)}</time>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function SelectField<T extends string>({ label, value, values, onChange }: { label: string; value: T; values: T[]; onChange: (value: T) => void }) {
  return (
    <label>
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value as T)}>
        {values.map((item) => <option key={item} value={item}>{item ? formatLabel(item) : "Unset"}</option>)}
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
