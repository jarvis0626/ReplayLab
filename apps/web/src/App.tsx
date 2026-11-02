import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import {
  Activity,
  ArrowLeft,
  ArrowUpRight,
  BookOpen,
  Box,
  ChevronRight,
  CircleDot,
  FlaskConical,
  FolderOpen,
  GitBranch,
  Layers3,
  LayoutDashboard,
  Plus,
  Settings2,
  ShieldCheck,
  Video,
  X,
} from "lucide-react";
import type { Health, Modality, Project } from "./types";
import { api } from "./services/api";
import { providerModels, providerName, usesCloud } from "./services/providers";
import { Badge, ErrorBanner, Spinner } from "./components/ui";
import { Dashboard } from "./pages/Dashboard";
import { Studio } from "./pages/Studio";
import { TaskWorkspace } from "./pages/TaskWorkspace";
const Practice = lazy(() => import("./pages/Practice").then((module) => ({ default: module.Practice })));
const EvaluationPage = lazy(() => import("./pages/Evaluation").then((module) => ({ default: module.EvaluationPage })));
import { LiveScreenAssistant } from "./pages/LiveScreenAssistant";

type Tab = "studio" | "task" | "practice" | "evaluation";
const tabs = [
  { id: "studio", title: "Demonstration", icon: Video },
  { id: "task", title: "Task & graph", icon: GitBranch },
  { id: "practice", title: "Guided practice", icon: Layers3 },
  { id: "evaluation", title: "Evaluation", icon: FlaskConical },
] as const;

export function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [project, setProject] = useState<Project | null>(null);
  const [tab, setTab] = useState<Tab>("studio");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [newProject, setNewProject] = useState(false);
  const [name, setName] = useState("");
  const [modality, setModality] = useState<Modality>("physical");
  const [settings, setSettings] = useState(false);
  const [consent, setConsent] = useState(false);
  const updateProject = useCallback((value: Project) => {
    setProject(value);
    setProjects((prev) => [value, ...prev.filter((p) => p.id !== value.id)]);
  }, []);
  const reload = useCallback(async () => {
    setLoading(true);
    setError("");
    const responses = await Promise.allSettled([api.health(), api.projects()]);
    if (responses[0].status === "fulfilled") setHealth(responses[0].value);
    else setError(responses[0].reason.message);
    if (responses[1].status === "fulfilled") setProjects(responses[1].value);
    else setError(responses[1].reason.message);
    setLoading(false);
  }, []);
  useEffect(() => {
    void reload();
  }, [reload]);
  useEffect(() => {
    setConsent(false);
  }, [project?.id]);
  useEffect(() => {
    if (!project || project.status !== "processing") return;
    const timer = window.setInterval(() => {
      void api
        .project(project.id)
        .then(updateProject)
        .catch((e: Error) => setError(e.message));
    }, 1800);
    return () => clearInterval(timer);
  }, [project, updateProject]);
  async function create(demo: false | true | "digital" = false) {
    setBusy(true);
    setError("");
    try {
      const value =
        demo === "digital"
          ? await api.digitalDemo()
          : demo
            ? await api.demo()
            : await api.create(name.trim(), modality);
      updateProject(value);
      setTab(demo ? "task" : "studio");
      setNewProject(false);
      setName("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function open(id: string) {
    setError("");
    try {
      updateProject(await api.project(id));
      setTab("studio");
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function remove(id: string) {
    setError("");
    try {
      await api.remove(id);
      setProjects((prev) => prev.filter((p) => p.id !== id));
      if (project?.id === id) setProject(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  const provider = health?.provider;
  const progress = project?.task?.steps.length
    ? Math.round(
        (project.completed_step_ids.length / project.task.steps.length) * 100,
      )
    : 0;

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <button
          className="brand"
          onClick={() => setProject(null)}
          aria-label="ReplayLab dashboard"
        >
          <span className="brand-mark">
            <Layers3 size={23} />
          </span>
          <span>
            Replay<span className="brand-light">Lab</span>
            <small>VISUAL LEARNING WORKSPACE</small>
          </span>
        </button>
        <div className="workspace-label">
          <span className="avatar">RL</span>
          <div>
            Personal workspace<small>Local development</small>
          </div>
          <ShieldCheck size={15} className="muted" />
        </div>
        <div className="nav-label">WORKSPACE</div>
        <nav aria-label="Main navigation">
          <button
            className={!project ? "nav-item active" : "nav-item"}
            onClick={() => setProject(null)}
          >
            <LayoutDashboard size={18} />
            Overview<span className="shortcut">⌘ 1</span>
          </button>
          <button className="nav-item" onClick={() => setNewProject(true)}>
            <Plus size={18} />
            New project
          </button>
        </nav>
        <div className="nav-label project-label">
          YOUR PROJECTS<span>{projects.length}</span>
        </div>
        <div className="project-nav">
          {projects.slice(0, 8).map((p) => (
            <button
              className={`nav-item ${p.id === project?.id ? "active" : ""}`}
              key={p.id}
              onClick={() => void open(p.id)}
            >
              <Box size={16} />
              <span className="truncate">{p.name}</span>
              <span className={`project-dot ${p.status}`} />
            </button>
          ))}
          {!projects.length && (
            <p className="sidebar-empty">Your demonstrations will live here.</p>
          )}
        </div>
        <div className="sidebar-bottom">
          <div className="local-note">
            <ShieldCheck size={17} />
            <div>
              Private by default
              <small>
                Media stays on your server until you consent to cloud
                processing.
              </small>
            </div>
          </div>
          <button className="nav-item" onClick={() => setSettings(true)}>
            <Settings2 size={17} />
            Provider settings
            <ChevronRight size={14} />
          </button>
          <div className="sidebar-footer">
            <span>ReplayLab</span>
            <span>v3.0 · Research preview</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="breadcrumbs">
            <FolderOpen size={16} />
            <span>Workspace</span>
            <ChevronRight size={13} />
            <strong>{project?.name ?? "Overview"}</strong>
          </div>
          <div className="topbar-status">
            <span
              className={`status-dot ${provider?.available ? "online" : ""}`}
            />
            <span>
              {provider
                ? provider.mode === "mock"
                  ? "Offline engine"
                  : provider.available
                    ? `${providerName(provider)} provider`
                    : provider.configured
                      ? `${providerName(provider)} access unverified`
                      : `${providerName(provider)} credentials missing`
                : "Connecting"}
            </span>
            <Badge variant={provider?.mode === "mock" ? "mock" : "neutral"}>
              {provider?.mode === "mock"
                ? "MOCK MODE"
                : provider && usesCloud(provider)
                  ? `${providerName(provider).toUpperCase()} MODE`
                  : "API"}
            </Badge>
            <button
              className="icon-button"
              aria-label="Open provider settings"
              onClick={() => setSettings(true)}
            >
              <Settings2 size={16} />
            </button>
          </div>
        </header>
        {error && (
          <div className="global-error">
            <ErrorBanner message={error} dismiss={() => setError("")} />
          </div>
        )}
        {!project ? (
          <Dashboard
            projects={projects}
            loading={loading}
            busy={busy}
            onNew={() => setNewProject(true)}
            onDemo={() => void create(true)}
            onDigitalDemo={() => void create("digital")}
            onOpen={(id) => void open(id)}
            onDelete={(id) => void remove(id)}
            onRefresh={() => void reload()}
          />
        ) : (
          <div className="workspace-page">
            <div className="workspace-heading">
              <div>
                <button className="back-link" onClick={() => setProject(null)}>
                  <ArrowLeft size={14} />
                  All projects
                </button>
                <div className="title-line">
                  <h1>{project.name}</h1>
                  <Badge variant={project.approved ? "pass" : "neutral"}>
                    {project.approved
                      ? "Approved task"
                      : project.task
                        ? "Needs review"
                        : "New project"}
                  </Badge>
                </div>
                <p className="muted">
                  From a demonstration to observable, verifiable steps.
                </p>
              </div>
              <div className="workspace-progress">
                <span>
                  {project.completed_step_ids.length} /{" "}
                  {project.task?.steps.length ?? 0} steps complete
                </span>
                <div className="progress-track">
                  <span style={{ width: `${progress}%` }} />
                </div>
              </div>
            </div>
            <nav className="workspace-tabs" aria-label="Project workspace">
              {tabs.map((item) => (
                <button
                  key={item.id}
                  onClick={() => setTab(item.id)}
                  className={tab === item.id ? "selected" : ""}
                >
                  <item.icon size={16} />
                  {item.title}
                  {item.id === "task" && project.task && (
                    <span className="tab-count">
                      {project.task.steps.length}
                    </span>
                  )}
                </button>
              ))}
            </nav>
            {project.error && <ErrorBanner message={project.error} />}
            {tab === "studio" && (
              <Studio
                project={project}
                provider={provider}
                consent={consent}
                onUpdate={updateProject}
                onTask={() => setTab("task")}
                onError={setError}
              />
            )}
            {tab === "task" && (
              <TaskWorkspace
                project={project}
                onUpdate={updateProject}
                onError={setError}
                onPractice={() => setTab("practice")}
              />
            )}
            {tab === "practice" &&
              (project.modality === "digital" ? (
                <LiveScreenAssistant
                  key={project.id}
                  project={project}
                  provider={provider}
                  onUpdate={updateProject}
                  onError={setError}
                  onReview={() => setTab("task")}
                />
              ) : (
                <Suspense fallback={<Spinner label="Loading physical practice…" />}><Practice
                  project={project}
                  provider={provider}
                  consent={consent}
                  onUpdate={updateProject}
                  onError={setError}
                  onReview={() => setTab("task")}
                /></Suspense>
              ))}
            {tab === "evaluation" && (
              <Suspense fallback={<Spinner label="Loading evaluation…" />}><EvaluationPage project={project} onError={setError} /></Suspense>
            )}
          </div>
        )}
        <footer className="page-footer">
          <span>
            <CircleDot size={12} />
            Evidence before confidence
          </span>
          <span>Physical + digital workflows · Research preview</span>
        </footer>
      </main>

      {newProject && (
        <div
          className="modal-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget) setNewProject(false);
          }}
        >
          <form
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="new-title"
            onSubmit={(e) => {
              e.preventDefault();
              void create();
            }}
          >
            <div className="modal-heading">
              <span className="panel-icon">
                <Box size={22} />
              </span>
              <button
                className="icon-button"
                type="button"
                onClick={() => setNewProject(false)}
                aria-label="Close dialog"
              >
                <X size={18} />
              </button>
            </div>
            <h2 id="new-title">Start with a demonstration.</h2>
            <p className="muted">
              Give your project a name. You can add a video in the demonstration
              studio.
            </p>
            <label htmlFor="project-name">Project name</label>
            <input
              id="project-name"
              autoFocus
              placeholder="e.g. Four-block tower assembly"
              value={name}
              maxLength={120}
              onChange={(e) => setName(e.target.value)}
              required
            />
            <label className="modality-label" htmlFor="project-modality">
              Workflow type
            </label>
            <select
              id="project-modality"
              value={modality}
              onChange={(e) => setModality(e.target.value as Modality)}
            >
              <option value="physical">
                Physical task · camera checkpoints
              </option>
              <option value="digital">
                Digital workflow · live screen guidance
              </option>
            </select>
            <div className="modal-actions">
              <button
                className="button secondary"
                type="button"
                onClick={() => setNewProject(false)}
              >
                Cancel
              </button>
              <button
                className="button primary"
                disabled={busy || !name.trim()}
              >
                {busy ? (
                  <Spinner label="Creating…" />
                ) : (
                  <>
                    Create project
                    <ArrowUpRight size={16} />
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      )}
      {settings && (
        <div className="modal-backdrop">
          <div
            className="modal settings-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="settings-title"
          >
            <div className="modal-heading">
              <span className="eyebrow">
                <Activity size={14} />
                INFERENCE ENGINE
              </span>
              <button
                className="icon-button"
                onClick={() => setSettings(false)}
                aria-label="Close settings"
              >
                <X size={18} />
              </button>
            </div>
            <h2 id="settings-title">Transparent by design.</h2>
            <p className="muted">
              Choose the source of observations. Verification rules stay
              deterministic in every mode. Credentials stay on the server.
            </p>
            <div className="provider-options">
              {(["mock", "nvidia", "meta"] as const).map((mode) => (
                <button
                  className={`provider-option ${provider?.mode === mode ? "selected" : ""}`}
                  disabled={busy}
                  key={mode}
                  onClick={async () => {
                    setBusy(true);
                    try {
                      setHealth(await api.provider(mode));
                      setConsent(false);
                    } catch (e) {
                      setError((e as Error).message);
                    } finally {
                      setBusy(false);
                    }
                  }}
                >
                  <span className="radio-indicator" />
                  <div>
                    <strong>
                      {mode === "mock" ? "Offline / mock" : mode === "nvidia" ? "NVIDIA-hosted Meta model" : "Meta Model API"}
                    </strong>
                    <small>
                      {mode === "mock"
                        ? "Local OCR for digital screens; labeled physical fixtures. No cloud inference."
                        : mode === "nvidia"
                          ? "Digital screenshot and tutorial-frame understanding. Requires server credentials; no SAM segmentation."
                          : "Muse Spark + SAM. Requires server credentials and verified provider access."}
                    </small>
                  </div>
                </button>
              ))}
            </div>
            {usesCloud(provider) && <p className="muted small">Model: {providerModels(provider)} · Host: {provider?.host ?? (provider?.mode === "nvidia" ? "integrate.api.nvidia.com" : "api.meta.ai")} · {provider?.live_verified ? "Live requests validated" : "Live access not yet validated"}. A configured key alone does not establish model availability.</p>}
            <div className="info-note">
              <BookOpen size={17} />
              <span>
                {provider?.message ??
                  "Provider status is unavailable. Start the backend and reconnect."}
              </span>
            </div>
            <label className="checkbox-row">
              <input
                type="checkbox"
                checked={consent}
                onChange={(e) => setConsent(e.target.checked)}
              />
              <span>
                {provider?.mode === "nvidia"
                  ? "I consent to sending this session’s sampled tutorial frames and supplied transcript to NVIDIA for cloud processing. Provider processing and retention terms apply; no cloud deletion or expiry guarantee is made. NVIDIA mode does not provide physical segmentation. Screen analysis requires its own project consent."
                  : "I consent to sending this session’s uploaded videos and checkpoint images to Meta for cloud processing. Local media and inference caches remain until project deletion. ReplayLab requests cloud file deletion after processing, with a one-hour cloud expiry fallback."}
              </span>
            </label>
            <button
              className="button primary full-width"
              onClick={() => setSettings(false)}
            >
              Save preferences
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
