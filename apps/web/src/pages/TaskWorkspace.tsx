import { useEffect, useMemo, useState } from "react";
import {
  Background,
  BackgroundVariant,
  Controls,
  MarkerType,
  Position,
  ReactFlow,
} from "@xyflow/react";
import {
  ArrowDown,
  ArrowRight,
  ArrowUp,
  Check,
  CheckCircle2,
  GitBranch,
  GripVertical,
  List,
  Plus,
  Save,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import type { Graph, Project, Rule, Step, Task } from "../types";
import { api } from "../services/api";
import { ScreenRulesEditor } from "../components/ScreenRulesEditor";
import {
  Badge,
  Empty,
  EvidenceImage,
  formatTime,
  Spinner,
} from "../components/ui";

interface Props {
  project: Project;
  onUpdate: (p: Project) => void;
  onError: (message: string) => void;
  onPractice: () => void;
}
export function TaskWorkspace({
  project,
  onUpdate,
  onError,
  onPractice,
}: Props) {
  const digital = project.modality === "digital";
  const [task, setTask] = useState<Task | null>(project.task);
  const [selectedId, setSelectedId] = useState(
    project.task?.steps[0]?.id ?? "",
  );
  const [graph, setGraph] = useState<Graph | null>(null);
  const [view, setView] = useState<"graph" | "list">("graph");
  const [dirty, setDirty] = useState(false);
  const [objectInput, setObjectInput] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    setTask(project.task);
    setDirty(false);
    setObjectInput({});
  }, [project.task]);
  useEffect(() => {
    if (project.task)
      void api
        .graph(project.id)
        .then(setGraph)
        .catch((e: Error) => onError(e.message));
  }, [project.id, project.task, project.completed_step_ids, onError]);
  const selected =
    task?.steps.find((s) => s.id === selectedId) ?? task?.steps[0];
  const selectedFrame = project.frames.find(
    (f) => f.id === selected?.reference_frame_id,
  );
  const flow = useMemo(() => {
    if (!graph) return { nodes: [], edges: [] };
    const depths: Record<string, number> = {};
    const rows: Record<number, number> = {};
    const nodes = graph.order.map((id) => {
      const step = graph.nodes.find((s) => s.id === id)!;
      const level =
        Math.max(-1, ...step.dependencies.map((d) => depths[d] ?? 0)) + 1;
      depths[id] = level;
      const row = rows[level] ?? 0;
      rows[level] = row + 1;
      return {
        id,
        position: { x: level * 225 + 20, y: row * 130 + 36 },
        data: {
          label: (
            <div className="flow-label">
              <span className="flow-step">
                STEP {graph.order.indexOf(id) + 1}
                <span>
                  {step.status === "completed" ? (
                    <CheckCircle2 size={13} />
                  ) : (
                    <span className="flow-node-dot" />
                  )}
                </span>
              </span>
              <strong>{step.title}</strong>
              <small>
                {formatTime(step.timestamp_start)}–
                {formatTime(step.timestamp_end)} ·{" "}
                {digital ? (step.screen_rules?.length ?? 0) : step.rules.length}{" "}
                rules
              </small>
            </div>
          ),
        },
        className: `task-flow-node ${step.status} ${id === selectedId ? "is-selected" : ""}`,
        style: { width: 190 },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
      };
    });
    const edges = graph.edges.map((edge) => ({
      id: `${edge.source}-${edge.target}`,
      source: edge.source,
      target: edge.target,
      animated: false,
      type: "smoothstep",
      style: { stroke: "#3f5362", strokeWidth: 1.5 },
      markerEnd: {
        type: MarkerType.ArrowClosed,
        color: "#3f5362",
        width: 16,
        height: 16,
      },
    }));
    return { nodes, edges };
  }, [graph, selectedId, digital]);
  function changeStep(patch: Partial<Step>) {
    if (!task || !selected) return;
    setTask({
      ...task,
      steps: task.steps.map((s) =>
        s.id === selected.id ? { ...s, ...patch } : s,
      ),
    });
    setDirty(true);
  }
  function changeRule(id: string, patch: Partial<Rule>) {
    if (selected)
      changeStep({
        rules: selected.rules.map((r) =>
          r.id === id ? { ...r, ...patch } : r,
        ),
      });
  }
  function addStep() {
    if (!task) return;
    const step: Step = {
      id: `step-${crypto.randomUUID()}`,
      title: "New step",
      description: "Describe the observable checkpoint.",
      dependencies: task.steps.length
        ? [task.steps[task.steps.length - 1].id]
        : [],
      timestamp_start: 0,
      timestamp_end: 0,
      reference_frame_id: project.frames[0]?.id ?? null,
      object_labels: [],
      rules: [],
      screen_rules: [],
      expected_state: "",
    };
    setTask({ ...task, steps: [...task.steps, step] });
    setSelectedId(step.id);
    setDirty(true);
    setView("list");
  }
  function removeStep() {
    if (!task || !selected) return;
    setTask({
      ...task,
      steps: task.steps
        .filter((s) => s.id !== selected.id)
        .map((s) => ({
          ...s,
          dependencies: s.dependencies.filter((d) => d !== selected.id),
        })),
    });
    setDirty(true);
  }
  function moveStep(direction: -1 | 1) {
    if (!task || !selected) return;
    const index = task.steps.indexOf(selected);
    const target = index + direction;
    if (target < 0 || target >= task.steps.length) return;
    const copy = [...task.steps];
    [copy[index], copy[target]] = [copy[target], copy[index]];
    setTask({ ...task, steps: copy });
    setDirty(true);
  }
  async function save() {
    if (!task) return;
    setBusy(true);
    try {
      onUpdate(await api.saveTask(project.id, task));
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function approve() {
    setBusy(true);
    try {
      onUpdate(await api.approve(project.id));
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  if (!task)
    return (
      <div className="panel">
        <Empty
          icon={<GitBranch size={28} />}
          title="A task needs a demonstration."
        >
          <p>
            Upload a video and generate task steps in the demonstration studio.
          </p>
        </Empty>
      </div>
    );
  return (
    <div className="task-workspace page-enter">
      {task.provenance.cloud_file_cleanup_pending === true && (
        <div className="info-note">
          Meta file cleanup is pending. Uploaded cloud files use a one-hour
          expiry fallback; server media remains until project deletion.
        </div>
      )}
      <div className={`approval-banner ${project.approved ? "approved" : ""}`}>
        <ShieldCheck size={22} />
        <div>
          <strong>
            {project.approved
              ? "Your task is reviewed and approved."
              : "Review the proposed steps before practice."}
          </strong>
          <p>
            {project.approved
              ? "Editing the task resets approval and completion so verification stays consistent."
              : "Check source evidence, dependencies, and observable rules. AI-proposed instructions are never approved automatically."}
          </p>
        </div>
        <button
          className={`button ${project.approved ? "secondary" : "primary"}`}
          disabled={dirty || busy}
          onClick={project.approved ? onPractice : () => void approve()}
        >
          {busy ? (
            <Spinner />
          ) : project.approved ? (
            <>
              Start practice
              <ArrowRight size={16} />
            </>
          ) : (
            <>
              <Check size={16} />
              Approve task
            </>
          )}
        </button>
      </div>
      <div className="task-topline">
        <div>
          <h2>{task.title}</h2>
          <p className="muted">{task.description}</p>
          <div className="object-chips">
            {task.objects.map((object) => (
              <Badge key={object} variant="neutral">
                <span className={`object-color ${object.split(" ")[0]}`} />
                {object}
              </Badge>
            ))}
            <Badge variant={task.provider_mode === "mock" ? "mock" : "cyan"}>
              {task.provider_mode.toUpperCase()} PROPOSAL
            </Badge>
          </div>
          {digital && <label className="workflow-version-label">Reference application/version (optional)<input aria-label="Reference application and version" maxLength={120} placeholder="e.g. CodeLab 1.0 — use visible source evidence" value={task.interface_version ?? ""} onChange={(event) => { setTask({ ...task, interface_version: event.target.value || null }); setDirty(true); }} /><small className="muted">Set only a version shown in the tutorial. A detected difference causes uncertainty.</small></label>}
        </div>
        <div className="row-actions">
          {dirty && <span className="unsaved">Unsaved changes</span>}
          <button
            className="button secondary compact"
            disabled={!dirty || busy}
            onClick={() => void save()}
          >
            <Save size={15} />
            Save changes
          </button>
        </div>
      </div>
      <div className="task-layout">
        <section className="panel graph-panel">
          <div className="panel-heading">
            <h2>
              <GitBranch size={17} />
              Action graph
              <span className="count-label">{task.steps.length}</span>
            </h2>
            <div className="segmented">
              <button
                onClick={() => setView("graph")}
                className={view === "graph" ? "selected" : ""}
                aria-label="Graph view"
              >
                <GitBranch size={15} />
              </button>
              <button
                onClick={() => setView("list")}
                className={view === "list" ? "selected" : ""}
                aria-label="List view"
              >
                <List size={15} />
              </button>
            </div>
          </div>
          {view === "graph" ? (
            <div className="flow-canvas" data-testid="task-graph">
              <ReactFlow
                nodes={flow.nodes}
                edges={flow.edges}
                fitView
                fitViewOptions={{ padding: 0.06 }}
                minZoom={0.3}
                maxZoom={1.4}
                colorMode="dark"
                onNodeClick={(_, node) => setSelectedId(node.id)}
                nodesDraggable={false}
                nodesConnectable={false}
                proOptions={{ hideAttribution: false }}
              >
                <Background
                  variant={BackgroundVariant.Dots}
                  gap={22}
                  size={1}
                  color="#2b3440"
                />
                <Controls showInteractive={false} />
              </ReactFlow>
              {dirty && (
                <div className="graph-draft-note">
                  Save changes to update the graph.
                </div>
              )}
            </div>
          ) : (
            <div className="step-list">
              {task.steps.map((step, i) => (
                <button
                  key={step.id}
                  className={`step-list-item ${selected?.id === step.id ? "selected" : ""}`}
                  onClick={() => setSelectedId(step.id)}
                >
                  <GripVertical size={16} />
                  <span
                    className={`step-number ${project.completed_step_ids.includes(step.id) ? "completed" : ""}`}
                  >
                    {project.completed_step_ids.includes(step.id) ? (
                      <Check size={14} />
                    ) : (
                      i + 1
                    )}
                  </span>
                  <div>
                    <strong>{step.title}</strong>
                    <small>
                      {formatTime(step.timestamp_start)}–
                      {formatTime(step.timestamp_end)} ·{" "}
                      {step.dependencies.length} prerequisite
                      {step.dependencies.length !== 1 ? "s" : ""}
                    </small>
                  </div>
                  <ArrowRight size={15} />
                </button>
              ))}
            </div>
          )}
          <div className="graph-footer">
            <div className="graph-legend">
              <span>
                <i className="completed" />
                Completed
              </span>
              <span>
                <i className="current" />
                Current
              </span>
              <span>
                <i />
                Pending
              </span>
            </div>
            <button className="button text-button compact" onClick={addStep}>
              <Plus size={15} />
              Add step
            </button>
          </div>
        </section>
        <aside className="panel step-editor">
          <div className="panel-heading">
            <h2>Checkpoint details</h2>
            <div className="row-actions">
              <button
                className="icon-button"
                aria-label="Move step up"
                disabled={!selected || task.steps.indexOf(selected) === 0}
                onClick={() => moveStep(-1)}
              >
                <ArrowUp size={15} />
              </button>
              <button
                className="icon-button"
                aria-label="Move step down"
                disabled={
                  !selected ||
                  task.steps.indexOf(selected) === task.steps.length - 1
                }
                onClick={() => moveStep(1)}
              >
                <ArrowDown size={15} />
              </button>
              <button
                className="icon-button danger-text"
                aria-label="Remove selected step"
                onClick={removeStep}
              >
                <Trash2 size={15} />
              </button>
            </div>
          </div>
          {selected && (
            <div className="editor-body">
              {selectedFrame && (
                <EvidenceImage
                  src={selectedFrame.url}
                  alt={`Reference evidence for ${selected.title}`}
                />
              )}
              <label>
                Step title
                <input
                  value={selected.title}
                  onChange={(e) => changeStep({ title: e.target.value })}
                />
              </label>
              <label>
                Instruction
                <textarea
                  rows={3}
                  value={selected.description}
                  onChange={(e) => changeStep({ description: e.target.value })}
                />
              </label>
              <div className="field-grid">
                <label>
                  Start (seconds)
                  <input
                    type="number"
                    min={0}
                    step={0.1}
                    value={selected.timestamp_start}
                    onChange={(e) =>
                      changeStep({ timestamp_start: Number(e.target.value) })
                    }
                  />
                </label>
                <label>
                  End (seconds)
                  <input
                    type="number"
                    min={0}
                    step={0.1}
                    value={selected.timestamp_end}
                    onChange={(e) =>
                      changeStep({ timestamp_end: Number(e.target.value) })
                    }
                  />
                </label>
              </div>
              {digital && (
                <label>
                  Expected visible UI state
                  <textarea
                    rows={3}
                    value={selected.expected_state ?? ""}
                    onChange={(e) =>
                      changeStep({ expected_state: e.target.value })
                    }
                  />
                </label>
              )}
              <label>
                Source reference
                <select
                  value={selected.reference_frame_id ?? ""}
                  onChange={(e) =>
                    changeStep({ reference_frame_id: e.target.value || null })
                  }
                >
                  <option value="">No reference frame</option>
                  {project.frames.map((f, i) => (
                    <option key={f.id} value={f.id}>
                      Frame {i + 1} · {formatTime(f.timestamp)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Objects (comma separated)
                <input
                  value={
                    objectInput[selected.id] ??
                    selected.object_labels.join(", ")
                  }
                  onChange={(e) => {
                    setObjectInput((prev) => ({
                      ...prev,
                      [selected.id]: e.target.value,
                    }));
                    changeStep({
                      object_labels: e.target.value
                        .split(",")
                        .map((s) => s.trim())
                        .filter(Boolean),
                    });
                  }}
                />
              </label>
              <fieldset>
                <legend>Prerequisites</legend>
                {task.steps
                  .filter((s) => s.id !== selected.id)
                  .map((step) => (
                    <label className="checkbox-row compact" key={step.id}>
                      <input
                        type="checkbox"
                        checked={selected.dependencies.includes(step.id)}
                        onChange={(e) =>
                          changeStep({
                            dependencies: e.target.checked
                              ? [...selected.dependencies, step.id]
                              : selected.dependencies.filter(
                                  (d) => d !== step.id,
                                ),
                          })
                        }
                      />
                      <span>{step.title}</span>
                    </label>
                  ))}
                {task.steps.length === 1 && (
                  <small className="muted">This is the only step.</small>
                )}
              </fieldset>
              {digital && (
                <ScreenRulesEditor
                  key={selected.id}
                  rules={selected.screen_rules ?? []}
                  onChange={(screen_rules) => changeStep({ screen_rules })}
                />
              )}
              {!digital && (
                <>
                  <div className="rule-heading">
                    <span className="field-label">Observable rules</span>
                    <button
                      className="icon-button"
                      aria-label="Add checkpoint rule"
                      onClick={() =>
                        changeStep({
                          rules: [
                            ...selected.rules,
                            {
                              id: `rule-${crypto.randomUUID()}`,
                              kind: "presence",
                              subject: selected.object_labels[0] ?? "red block",
                              tolerance: 0.05,
                            },
                          ],
                        })
                      }
                    >
                      <Plus size={16} />
                    </button>
                  </div>
                  {!selected.rules.length && (
                    <p className="muted small">
                      Add rules before approval. No rules means no verified
                      completion.
                    </p>
                  )}
                  {selected.rules.map((rule, i) => (
                    <div className="rule-editor" key={rule.id}>
                      <div className="row-between">
                        <span className="rule-index">RULE {i + 1}</span>
                        <button
                          className="icon-button"
                          aria-label={`Remove rule ${i + 1}`}
                          onClick={() =>
                            changeStep({
                              rules: selected.rules.filter(
                                (r) => r.id !== rule.id,
                              ),
                            })
                          }
                        >
                          <Trash2 size={13} />
                        </button>
                      </div>
                      <div className="field-grid">
                        <label>
                          Relationship
                          <select
                            value={rule.kind}
                            onChange={(e) =>
                              changeRule(rule.id, {
                                kind: e.target.value as Rule["kind"],
                              })
                            }
                          >
                            {[
                              "presence",
                              "count",
                              "above",
                              "below",
                              "left",
                              "right",
                              "near",
                              "aligned",
                              "color",
                            ].map((kind) => (
                              <option key={kind}>{kind}</option>
                            ))}
                          </select>
                        </label>
                        <label>
                          Subject
                          <input
                            value={rule.subject}
                            onChange={(e) =>
                              changeRule(rule.id, { subject: e.target.value })
                            }
                          />
                        </label>
                      </div>
                      {!["presence", "count", "color"].includes(rule.kind) && (
                        <label>
                          Target object
                          <input
                            value={rule.target ?? ""}
                            onChange={(e) =>
                              changeRule(rule.id, {
                                target: e.target.value || null,
                              })
                            }
                          />
                        </label>
                      )}
                      {["count", "color"].includes(rule.kind) && (
                        <label>
                          Expected value
                          <input
                            type={rule.kind === "count" ? "number" : "text"}
                            value={
                              rule.value === null || rule.value === undefined
                                ? ""
                                : String(rule.value)
                            }
                            onChange={(e) =>
                              changeRule(rule.id, {
                                value:
                                  rule.kind === "count"
                                    ? Number(e.target.value)
                                    : e.target.value,
                              })
                            }
                          />
                        </label>
                      )}
                      <label>
                        Tolerance (normalized)
                        <input
                          type="number"
                          step={0.01}
                          min={0.01}
                          max={0.5}
                          value={rule.tolerance}
                          onChange={(e) =>
                            changeRule(rule.id, {
                              tolerance: Number(e.target.value),
                            })
                          }
                        />
                      </label>
                    </div>
                  ))}
                </>
              )}
              <p className="editor-note">
                The server validates missing dependencies, cycles, and
                checkpoint rules when saving.
              </p>
            </div>
          )}
        </aside>
      </div>
    </div>
  );
}
