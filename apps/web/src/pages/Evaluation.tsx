import { useEffect, useState } from "react";
import { BarChart3, CheckCircle2, FlaskConical, RefreshCw } from "lucide-react";
import type { Evaluation, Project, Verdict } from "../types";
import { api } from "../services/api";
import { Badge, Empty, Spinner, VerdictBadge } from "../components/ui";

export function EvaluationPage({
  project,
  onError,
}: {
  project: Project;
  onError: (message: string) => void;
}) {
  const [data, setData] = useState<Evaluation | null>(null);
  const [busy, setBusy] = useState(true);
  const [selectedId, setSelectedId] = useState("");
  async function load() {
    setBusy(true);
    try {
      setData(await api.evaluation(project.id));
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    void load(); /* load only when changing project */
  }, [project.id]);
  const labels: Verdict[] = ["pass", "fail", "uncertain"];
  const selected = data?.details.find((c) => c.id === selectedId);
  return (
    <div className="evaluation-page page-enter">
      <div className="section-heading">
        <div>
          <div className="eyebrow">MEASURED, NEVER ASSUMED</div>
          <h2>Verification evaluation</h2>
          <p>
            Controlled fixtures test the deterministic engine, not real-world
            model accuracy.
          </p>
        </div>
        <button
          className="button secondary"
          onClick={() => void load()}
          disabled={busy}
        >
          <RefreshCw size={15} />
          Run evaluation
        </button>
      </div>
      {busy ? (
        <div className="panel loading-panel">
          <Spinner label="Evaluating labeled scenarios…" />
        </div>
      ) : data ? (
        <>
          <div className="evaluation-stats">
            <div className="panel eval-score">
              <span className="stat-label">Expected verdicts matched</span>
              <strong>
                {data.correct}
                <small> / {data.sample_size}</small>
              </strong>
              <span className="muted">
                {((data.accuracy ?? 0) * 100).toFixed(1)}% agreement · curated
                fixtures
              </span>
            </div>
            {labels.map((status) => (
              <div className={`panel verdict-stat ${status}`} key={status}>
                <VerdictBadge status={status} />
                <strong>
                  {data.details.filter((c) => c.predicted === status).length}
                </strong>
                <span className="muted">Predicted verdicts</span>
              </div>
            ))}
          </div>
          <div className="evaluation-layout">
            <section className="panel">
              <div className="panel-heading">
                <h2>
                  <FlaskConical size={17} />
                  Labeled scenarios
                </h2>
                <Badge>{data.sample_size} cases</Badge>
              </div>
              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Scenario</th>
                      <th>Expected</th>
                      <th>Predicted</th>
                      <th>Match</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.details.map((c) => (
                      <tr
                        key={c.id}
                        className={selectedId === c.id ? "selected" : ""}
                      >
                        <td>
                          <button
                            className="table-case-button"
                            onClick={() => setSelectedId(c.id)}
                          >
                            {c.title}
                          </button>
                        </td>
                        <td>
                          <VerdictBadge status={c.expected} />
                        </td>
                        <td>
                          <VerdictBadge status={c.predicted} />
                        </td>
                        <td>
                          {c.correct ? (
                            <CheckCircle2
                              className="pass-text"
                              size={17}
                              aria-label="Matches expected"
                            />
                          ) : (
                            <span className="danger-text">Mismatch</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {selected && (
                <div className="case-diagnostic">
                  <strong>{selected.title}</strong>
                  <p>{selected.explanation}</p>
                </div>
              )}
            </section>
            <aside className="evaluation-aside">
              <section className="panel">
                <div className="panel-heading">
                  <h2>
                    <BarChart3 size={17} />
                    Confusion matrix
                  </h2>
                </div>
                <div className="matrix-wrap">
                  <p className="muted small">
                    Rows: expected · Columns: predicted
                  </p>
                  <table className="confusion-table">
                    <thead>
                      <tr>
                        <th />
                        {labels.map((s) => (
                          <th key={s}>{s}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {labels.map((expected) => (
                        <tr key={expected}>
                          <th>{expected}</th>
                          {labels.map((predicted) => (
                            <td
                              className={
                                expected === predicted ? "diagonal" : ""
                              }
                              key={predicted}
                            >
                              {data.confusion_matrix[expected]?.[predicted] ??
                                0}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
              <section className="panel evaluation-limits">
                <h3>What this measures</h3>
                <ul>
                  {data.limitations.map((limitation, i) => (
                    <li key={i}>{limitation}</li>
                  ))}
                </ul>
                <p>
                  Fixture observations are explicitly supplied. A matching
                  verdict does not establish SAM detection accuracy or general
                  assembly understanding.
                </p>
              </section>
            </aside>
          </div>
        </>
      ) : (
        <div className="panel">
          <Empty
            icon={<FlaskConical size={25} />}
            title="Evaluation is unavailable."
          >
            <p>Check the API connection, then run evaluation again.</p>
          </Empty>
        </div>
      )}
    </div>
  );
}
