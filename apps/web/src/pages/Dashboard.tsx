import {
  ArrowDown,
  ArrowRight,
  ArrowUpRight,
  Box,
  CirclePlay,
  Clock3,
  GitBranch,
  Layers3,
  MoreHorizontal,
  Plus,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Trash2,
  Video,
} from "lucide-react";
import { useState } from "react";
import type { Project } from "../types";
import { Badge, Empty, Spinner } from "../components/ui";

interface Props {
  projects: Project[];
  loading: boolean;
  busy: boolean;
  onNew: () => void;
  onDemo: () => void;
  onOpen: (id: string) => void;
  onDelete: (id: string) => void;
  onRefresh: () => void;
}
export function Dashboard({
  projects,
  loading,
  busy,
  onNew,
  onDemo,
  onOpen,
  onDelete,
  onRefresh,
}: Props) {
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const tasks = projects.filter((p) => p.task).length;
  const steps = projects.reduce((n, p) => n + p.completed_step_ids.length, 0);
  return (
    <div className="dashboard page-enter">
      <div className="dashboard-heading">
        <div>
          <div className="eyebrow">YOUR LEARNING LAB</div>
          <h1>
            Teach once.
            <br />
            <span>Learn by doing.</span>
          </h1>
          <p>
            Turn physical demonstrations into guided practice.
            <br className="desktop-break" /> Every step connected to evidence.
          </p>
        </div>
        <button className="button primary" onClick={onNew}>
          <Plus size={17} />
          New project
        </button>
      </div>
      <div className="hero-workbench">
        <div className="hero-copy">
          <Badge variant="cyan">
            <span className="status-dot online" />
            THE REPLAYLAB WORKFLOW
          </Badge>
          <h2>
            Make know-how
            <br />
            something you can see.
          </h2>
          <p>
            Capture a process. Review the action graph.
            <br />
            Practice with visual checkpoints that explain why.
          </p>
          <button
            className="button text-button"
            onClick={onDemo}
            disabled={busy}
          >
            {busy ? (
              <Spinner label="Preparing sample…" />
            ) : (
              <>
                Explore the sample project
                <ArrowUpRight size={16} />
              </>
            )}
          </button>
        </div>
        <div
          className="workflow-visual"
          aria-label="Demonstration to graph to verification workflow"
        >
          <div className="mini-window">
            <div className="mini-window-bar">
              <span />
              <span />
              <span />
              <small>tabletop-assembly.demo</small>
            </div>
            <div className="block-scene">
              <span className="scene-grid" />
              <span className="toy-block red" />
              <span className="toy-block blue" />
              <span className="toy-block green" />
              <span className="toy-block yellow" />
              <span className="scene-target">
                <span>REFERENCE STATE</span>
              </span>
            </div>
            <div className="mini-timeline">
              <CirclePlay size={15} />
              <span>
                <i />
              </span>
              <small>00:08 / 00:12</small>
            </div>
          </div>
          <div className="workflow-connector">
            <span />
            <ArrowRight size={16} />
            <span />
          </div>
          <div className="mini-graph">
            <div>
              <span className="graph-point" />
              <Video size={15} />
              Observe<span className="mini-check">01</span>
            </div>
            <span className="mini-line" />
            <div>
              <span className="graph-point" />
              <GitBranch size={15} />
              Understand<span className="mini-check">02</span>
            </div>
            <span className="mini-line" />
            <div className="verified">
              <ShieldCheck size={15} />
              Verify with evidence<span className="mini-check">✓</span>
            </div>
            <span className="fixture-caption">
              Illustrated workflow · not model output
            </span>
          </div>
        </div>
      </div>
      <div className="stat-grid">
        <div className="stat-card">
          <span className="stat-icon">
            <Box size={18} />
          </span>
          <div>
            <span className="stat-label">Projects</span>
            <strong>{projects.length.toString().padStart(2, "0")}</strong>
          </div>
          <span className="stat-caption">Your demonstrations</span>
        </div>
        <div className="stat-card">
          <span className="stat-icon">
            <GitBranch size={18} />
          </span>
          <div>
            <span className="stat-label">Structured tasks</span>
            <strong>{tasks.toString().padStart(2, "0")}</strong>
          </div>
          <span className="stat-caption">Ready to review</span>
        </div>
        <div className="stat-card">
          <span className="stat-icon">
            <ShieldCheck size={18} />
          </span>
          <div>
            <span className="stat-label">Verified steps</span>
            <strong>{steps.toString().padStart(2, "0")}</strong>
          </div>
          <span className="stat-caption">Evidence-grounded progress</span>
        </div>
      </div>
      <section className="recent-section">
        <div className="section-heading">
          <div>
            <h2>
              Recent projects{" "}
              <span className="count-label">{projects.length}</span>
            </h2>
            <p>Continue where your last demonstration left off.</p>
          </div>
          <div className="row-actions">
            <button
              className="icon-button"
              onClick={onRefresh}
              aria-label="Refresh projects"
            >
              <RefreshCw size={16} />
            </button>
            <button className="button secondary compact" onClick={onNew}>
              <Plus size={15} />
              Create project
            </button>
          </div>
        </div>
        {loading ? (
          <div className="loading-panel">
            <Spinner label="Loading your workspace…" />
          </div>
        ) : projects.length ? (
          <div className="project-grid">
            {projects.map((project) => (
              <article className="project-card" key={project.id}>
                <button
                  className="project-card-main"
                  onClick={() => onOpen(project.id)}
                >
                  <div className="project-thumbnail">
                    {project.frames[0] ? (
                      <img
                        src={project.frames[0].url}
                        alt={`${project.name} reference`}
                      />
                    ) : (
                      <div className="project-placeholder">
                        <Video size={30} />
                        <span>DEMONSTRATION</span>
                      </div>
                    )}
                    <Badge
                      variant={
                        project.status === "ready"
                          ? "pass"
                          : project.status === "error"
                            ? "fail"
                            : "neutral"
                      }
                    >
                      {project.status === "ready"
                        ? "Ready"
                        : project.status === "new"
                          ? "Awaiting video"
                          : project.status === "processing"
                            ? "Processing"
                            : "Needs attention"}
                    </Badge>
                  </div>
                  <div className="project-card-content">
                    <div className="project-title">
                      <h3>{project.name}</h3>
                      <ArrowUpRight size={16} />
                    </div>
                    <div className="project-meta">
                      <span>
                        <Layers3 size={13} />
                        {project.task?.steps.length ?? 0} steps
                      </span>
                      <span>
                        <Clock3 size={13} />
                        {new Date(project.created_at).toLocaleDateString("en", {
                          month: "short",
                          day: "numeric",
                        })}
                      </span>
                    </div>
                    <div className="project-card-progress">
                      <div className="progress-track">
                        <span
                          style={{
                            width: `${project.task?.steps.length ? (project.completed_step_ids.length / project.task.steps.length) * 100 : 0}%`,
                          }}
                        />
                      </div>
                      <span>
                        {project.completed_step_ids.length}/
                        {project.task?.steps.length ?? 0}
                      </span>
                    </div>
                  </div>
                </button>
                <button
                  className="project-menu icon-button"
                  aria-label={`Delete ${project.name}`}
                  onClick={() => setDeleteId(project.id)}
                >
                  <MoreHorizontal size={18} />
                </button>
              </article>
            ))}
            <button className="new-project-card" onClick={onNew}>
              <span>
                <Plus size={22} />
              </span>
              <strong>A new way to learn</strong>
              <small>Add your next demonstration</small>
            </button>
          </div>
        ) : (
          <div className="first-project">
            <Empty
              icon={<Video size={24} />}
              title="Your first demonstration starts here."
            >
              <p>
                Upload a short tabletop video, or explore the labeled sample.
              </p>
              <div className="empty-actions">
                <button className="button primary" onClick={onNew}>
                  <Plus size={15} />
                  New project
                </button>
                <button
                  className="button secondary"
                  onClick={onDemo}
                  disabled={busy}
                >
                  Open sample
                  <ArrowRight size={15} />
                </button>
              </div>
            </Empty>
          </div>
        )}
      </section>
      <div className="research-note">
        <span className="research-icon">
          <Sparkles size={18} />
        </span>
        <div>
          <strong>Built for observable learning.</strong>
          <span>
            PASS when evidence supports it. FAIL for a visible mismatch.
            UNCERTAIN when the camera cannot tell.
          </span>
        </div>
        <ArrowDown size={17} />
      </div>
      {deleteId && (
        <div className="modal-backdrop">
          <div
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="delete-title"
          >
            <span className="panel-icon danger">
              <Trash2 size={22} />
            </span>
            <h2 id="delete-title">Delete this project?</h2>
            <p className="muted">
              This removes its uploaded media, task, attempts, and verification
              history from this server.
            </p>
            <div className="modal-actions">
              <button
                className="button secondary"
                onClick={() => setDeleteId(null)}
              >
                Cancel
              </button>
              <button
                className="button danger"
                onClick={() => {
                  onDelete(deleteId);
                  setDeleteId(null);
                }}
              >
                Delete project
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
