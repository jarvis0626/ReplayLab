import { useState } from "react";
import { ClipboardList, Flag, History } from "lucide-react";
import type { Verdict, WorkflowVerification } from "../types";
import { api } from "../services/api";
import { Badge, Spinner, VerdictBadge } from "./ui";

const label = (value: string) => value.replaceAll("_", " ");

export function EvidenceInspector({ verification, onError }: {
  verification?: WorkflowVerification | null;
  onError?: (message: string) => void;
}) {
  const [reporting, setReporting] = useState(false);
  const [expected, setExpected] = useState<Verdict>("uncertain");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");
  if (!verification) return null;
  const record = verification;
  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.reportVerification(record.workflow_id, record.id, expected, notes.trim());
      setSaved(true);
      setReporting(false);
    } catch (reason) {
      const message = (reason as Error).message;
      setError(message);
      onError?.(message);
    } finally { setBusy(false); }
  }
  return <div className="verification-inspector">
    <div className="verification-trace-meta">
      <span><ClipboardList size={14} /> Decision trace</span>
      <span>{record.latency_ms.toFixed(0)} ms</span>
      <Badge>{record.retained ? "SAVED EVIDENCE" : "SESSION EVIDENCE"}</Badge>
    </div>
    {record.mismatch_classification && <p className="mismatch-classification">{label(record.mismatch_classification)}</p>}
    {record.uncertainty_reasons.length > 0 && <div className="uncertainty-reasons"><strong>{record.verdict === "uncertain" ? "Why ReplayLab abstained" : "Limits of the available evidence"}</strong><ul>{record.uncertainty_reasons.map((reason, index) => <li key={index}>{reason}</li>)}</ul></div>}
    <details>
      <summary>Inspect decision and source evidence</summary>
      <div className="trace-conditions">
        <div><h3>Expected conditions</h3><ul>{record.expected_conditions.map((value, index) => <li key={index}>{value}</li>)}</ul></div>
        <div><h3>Observed conditions</h3>{record.observed_conditions.length ? <ul>{record.observed_conditions.map((value, index) => <li key={index}>{value}</li>)}</ul> : <p>No adequate visible observations.</p>}</div>
      </div>
      {record.constraints.map((constraint) => <div className="trace-constraint" key={constraint.id}><VerdictBadge status={constraint.verdict} /><div><p><strong>Expected:</strong> {constraint.expected}</p><p><strong>Observed:</strong> {constraint.observed}</p>{constraint.correction && <p className="rule-correction">{constraint.correction}</p>}</div></div>)}
      <h3>Evidence references</h3>
      {record.evidence_references.length ? <ul className="trace-evidence">{record.evidence_references.map((reference) => <li key={reference.id}><strong>{label(reference.kind)}</strong> · {reference.source}{reference.timestamp != null ? ` · ${reference.timestamp.toFixed(1)}s` : ""}<p>{reference.text}</p></li>)}</ul> : <p>No supporting evidence references were available.</p>}
      <p className="muted small">Observation: {record.provider.observation} · Explanation: {record.provider.explanation}. The deterministic verifier owns the verdict.</p>
      <p className="muted small">{record.retained ? "Up to 100 relevant redacted decisions are saved until project deletion or history eviction; digital screenshots are never saved." : "Screen-session evidence is temporary unless you explicitly choose to save it."}</p>
      <small className="muted">Decision {record.id} · {record.modality} workflow · {new Date(record.created_at).toLocaleString()}</small>
    </details>
    <div className="trace-feedback">
      {saved ? <p role="status">Your evaluation report was saved. It does not change the verdict or mark this step complete.</p> : <button className="button text-button compact" onClick={() => setReporting(!reporting)}><Flag size={13} /> Report incorrect evaluation</button>}
      {reporting && <form onSubmit={(event) => void submit(event)}>
        <label>Expected verdict<select aria-label="Expected verdict for this evaluation" value={expected} onChange={(event) => setExpected(event.target.value as Verdict)}><option value="uncertain">UNCERTAIN</option><option value="pass">PASS</option><option value="fail">FAIL</option></select></label>
        <label>What did ReplayLab miss?<textarea aria-label="Evaluation report notes" value={notes} onChange={(event) => setNotes(event.target.value)} maxLength={1000} rows={3} placeholder="Describe the visible evidence. Avoid passwords or personal information." /></label>
        <p className="muted small">Up to 100 reports are stored locally until project deletion or report eviction.</p>
        <button className="button secondary compact" disabled={busy}>{busy ? <Spinner /> : <Flag size={13} />} Save evaluation report</button>
      </form>}
      {error && <p role="alert" className="danger-text">{error}</p>}
    </div>
  </div>;
}

export function VerificationHistory({ projectId, refreshKey = "", onError }: {
  projectId: string;
  refreshKey?: string;
  onError: (message: string) => void;
}) {
  const [records, setRecords] = useState<WorkflowVerification[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [selected, setSelected] = useState<string>("");
  async function load() {
    setBusy(true);
    try { setRecords(await api.verifications(projectId)); }
    catch (reason) { onError((reason as Error).message); }
    finally { setBusy(false); }
  }
  const current = records?.find((record) => record.id === selected);
  return <section className="panel verification-history" key={`${projectId}-${refreshKey}`}>
    <div className="panel-heading"><h2><History size={16} /> Saved verification history</h2><button className="button text-button compact" disabled={busy} onClick={() => void load()}>{busy ? <Spinner /> : records ? "Refresh history" : "Load saved evidence"}</button></div>
    {records && <><p className="muted small history-disclosure">{records.length} saved decisions. Only explicitly retained digital evidence appears here; no digital screenshots are stored.</p><div className="trace-history-list">{records.map((record) => <button key={record.id} className={selected === record.id ? "selected" : ""} onClick={() => setSelected(record.id)}><VerdictBadge status={record.verdict} /><span>{record.step_id}</span><time>{new Date(record.created_at).toLocaleTimeString()}</time></button>)}</div>{current && <EvidenceInspector key={current.id} verification={current} onError={onError} />}</>}
  </section>;
}
