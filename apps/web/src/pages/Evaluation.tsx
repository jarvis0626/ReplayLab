import { useCallback, useEffect, useRef, useState } from "react";
import { BarChart3, CheckCircle2, FlaskConical, RefreshCw } from "lucide-react";
import type { Evaluation, Project, Verdict } from "../types";
import { api } from "../services/api";
import { Badge, Empty, Spinner, VerdictBadge } from "../components/ui";

const percent = (value: number | null | undefined) => value == null ? "N/A" : `${(value * 100).toFixed(1)}%`;
const milliseconds = (value: number | null | undefined) => value == null ? "N/A" : `${Math.round(value).toLocaleString()} ms`;
type Suite = "digital" | "physical";

export function EvaluationPage({ project, onError }: {
  project: Project;
  onError: (message: string) => void;
}) {
  const [suite, setSuite] = useState<Suite>(project.modality === "digital" ? "digital" : "physical");
  const [data, setData] = useState<Evaluation | null>(null);
  const [busy, setBusy] = useState(true);
  const [running, setRunning] = useState(false);
  const [selectedId, setSelectedId] = useState("");
  const generation = useRef(0);
  const errorHandler = useRef(onError);
  errorHandler.current = onError;
  const load = useCallback(async (rerun = false) => {
    const current = ++generation.current;
    setBusy(true);
    setRunning(rerun);
    try {
      const value = suite === "digital"
        ? await (rerun ? api.runDigitalEvaluation() : api.digitalEvaluation())
        : await api.evaluation(project.id);
      if (current === generation.current) setData(value);
    } catch (reason) {
      if (current === generation.current) errorHandler.current((reason as Error).message);
    } finally {
      if (current === generation.current) { setBusy(false); setRunning(false); }
    }
  }, [project.id, suite]);
  useEffect(() => {
    setData(null);
    setSelectedId("");
    void load();
    return () => { generation.current++; };
  }, [load]);
  const labels: Verdict[] = ["pass", "fail", "uncertain"];
  const selected = data?.details.find((item) => item.id === selectedId);
  const digital = suite === "digital";
  return <div className="evaluation-page page-enter">
    <div className="section-heading">
      <div><div className="eyebrow">MEASURED, NEVER ASSUMED</div><h2>Verification evaluation</h2><p>{digital ? "Captured browser pixels, local OCR, and deterministic decisions." : "Controlled fixtures test the deterministic engine, not real-world model accuracy."}</p></div>
      <button className="button secondary" onClick={() => void load(true)} disabled={busy}><RefreshCw size={15} />Run evaluation</button>
    </div>
    <div className="evaluation-suite-picker" role="group" aria-label="Evaluation dataset">
      <button className="button secondary compact" aria-pressed={digital} onClick={() => setSuite("digital")}>Digital screen captures</button>
      <button className="button secondary compact" aria-pressed={!digital} onClick={() => setSuite("physical")}>Physical rule fixtures</button>
    </div>
    {busy ? <div className="panel loading-panel"><Spinner label={running && digital ? "Running OCR on captured cases. This may take a minute…" : "Loading measured evaluation…"} /></div> : data ? <>
      {digital && <div className="panel evaluation-method"><Badge variant="cyan">LOCAL OCR · CAPTURED BROWSER PIXELS</Badge><p>Controlled CodeLab attempts with labels authored before inference. These are development-team labels, not an independent human study or a live Meta evaluation.</p><p className="muted">{data.dataset}{data.measured_at ? ` · Measured ${new Date(data.measured_at).toLocaleString()}` : ""} · {data.sample_size} completed{data.target_size ? ` / ${data.target_size} target cases` : ""}. Re-running processes the same saved captures; it does not create new attempts.</p></div>}
      <div className="evaluation-stats">
        <div className="panel eval-score"><span className="stat-label">Expected verdicts matched</span><strong>{data.correct}<small> / {data.sample_size}</small></strong><span className="muted">{percent(data.accuracy)} agreement · {digital ? "controlled captures" : "curated fixtures"}</span></div>
        {labels.map((status) => <div className={`panel verdict-stat ${status}`} key={status}><VerdictBadge status={status} /><strong>{data.details.filter((item) => item.predicted === status).length}</strong><span className="muted">Predicted verdicts</span></div>)}
      </div>
      {digital && <div className="calibration-stats">
        <div className="panel calibration-stat"><span className="stat-label">Decisive accuracy</span><strong>{percent(data.decisive_accuracy)}</strong><span className="muted">Correct decisive predictions / {data.decisive_predictions ?? 0} PASS or FAIL predictions.<br />PASS ↔ FAIL errors: {data.decisive_misclassifications ?? 0}</span></div>
        <div className="panel calibration-stat"><span className="stat-label">False certainty</span><strong>{percent(data.false_certainty_rate)}</strong><span className="muted">{data.false_certainty_count ?? 0} decisive predictions / {data.uncertain_ground_truth_count ?? 0} ground-truth UNCERTAIN cases.</span></div>
        <div className="panel calibration-stat"><span className="stat-label">Uncertainty recall</span><strong>{percent(data.uncertainty_recall)}</strong><span className="muted">Ground-truth UNCERTAIN cases receiving UNCERTAIN. Empty denominators display N/A.</span></div>
        <div className="panel calibration-stat"><span className="stat-label">Response latency</span><strong>{milliseconds(data.latency_ms?.median)}</strong><span className="muted">Median · p95 {milliseconds(data.latency_ms?.p95)}<br />n = {data.latency_ms?.sample_size ?? 0} checkpoint submissions</span></div>
      </div>}
      <div className="evaluation-layout">
        <section className="panel"><div className="panel-heading"><h2><FlaskConical size={17} />Labeled scenarios</h2><Badge>{data.sample_size} cases</Badge></div>
          <div className="table-scroll"><table><thead><tr><th>Scenario</th><th>Expected</th><th>Predicted</th><th>Match</th></tr></thead><tbody>{data.details.map((item) => <tr key={item.id} className={selectedId === item.id ? "selected" : ""}><td><button className="table-case-button" onClick={() => setSelectedId(item.id)}>{item.title}</button>{item.processing_latency_ms != null && <div className="case-latency">{milliseconds(item.processing_latency_ms)}</div>}</td><td><VerdictBadge status={item.expected} /></td><td><VerdictBadge status={item.predicted} /></td><td>{item.correct ? <CheckCircle2 className="pass-text" size={17} aria-label="Matches expected" /> : <span className="danger-text">Mismatch</span>}</td></tr>)}</tbody></table></div>
          {selected && <div className="case-diagnostic"><strong>{selected.title}</strong><p>{selected.explanation}</p>{selected.category && <Badge>{selected.category.replaceAll("_", " ")}</Badge>}{selected.screenshot_url && <a href={selected.screenshot_url} target="_blank" rel="noopener noreferrer"><img src={selected.screenshot_url} alt={`Actual evaluation capture: ${selected.title}`} /></a>}{selected.expected_conditions?.length ? <><h3>Expected conditions</h3><ul>{selected.expected_conditions.map((value, index) => <li key={index}>{value}</li>)}</ul></> : null}{selected.observed_conditions?.length ? <><h3>Observed conditions</h3><ul>{selected.observed_conditions.map((value, index) => <li key={index}>{value}</li>)}</ul></> : null}{selected.evidence?.length ? <><h3>Decision evidence</h3><ul>{selected.evidence.map((value, index) => <li key={index}>{value}</li>)}</ul></> : null}{selected.failure_notes?.map((note, index) => <p key={index} className="screen-warning">{note}</p>)}</div>}
        </section>
        <aside className="evaluation-aside"><section className="panel"><div className="panel-heading"><h2><BarChart3 size={17} />Confusion matrix</h2></div><div className="matrix-wrap"><p className="muted small">Rows: expected · Columns: predicted</p><table className="confusion-table"><thead><tr><th />{labels.map((status) => <th key={status}>{status}</th>)}</tr></thead><tbody>{labels.map((expected) => <tr key={expected}><th>{expected}</th>{labels.map((predicted) => <td key={predicted} className={expected === predicted ? "diagonal" : ""}>{data.confusion_matrix[expected]?.[predicted] ?? 0}</td>)}</tr>)}</tbody></table></div></section>
          <section className="panel evaluation-limits"><h3>What this measures</h3><ul>{data.limitations.map((limitation, index) => <li key={index}>{limitation}</li>)}</ul><p>{digital ? "A small controlled sandbox set cannot establish accuracy across real software, new interfaces, or live Meta models. All failures remain visible in this report." : "Fixture observations are explicitly supplied. A matching verdict does not establish SAM detection accuracy or general assembly understanding."}</p></section>
        </aside>
      </div>
    </> : <div className="panel"><Empty icon={<FlaskConical size={25} />} title="Evaluation is unavailable."><p>Check the API connection, then run evaluation again.</p></Empty></div>}
  </div>;
}
