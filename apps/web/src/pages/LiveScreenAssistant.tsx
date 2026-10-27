import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  ExternalLink,
  EyeOff,
  MessageSquare,
  Monitor,
  Pause,
  Play,
  RefreshCw,
  Send,
  ShieldCheck,
  Square,
  Upload,
  Volume2,
  VolumeX,
  X,
} from "lucide-react";
import type { Project, Provider, ScreenCheck } from "../types";
import { api } from "../services/api";
import {
  Badge,
  Empty,
  EvidenceImage,
  Spinner,
  VerdictBadge,
} from "../components/ui";
import { useScreenCapture } from "../hooks/useScreenCapture";
import type { Redaction } from "../hooks/useScreenCapture";

interface Props {
  project: Project;
  provider?: Provider;
  onUpdate: (project: Project) => void;
  onError: (message: string) => void;
  onReview: () => void;
}
export function LiveScreenAssistant({
  project,
  provider,
  onUpdate,
  onError,
  onReview,
}: Props) {
  const steps = project.task?.steps ?? [];
  const available = steps.filter(
    (step) =>
      !project.completed_step_ids.includes(step.id) &&
      step.dependencies.every((id) => project.completed_step_ids.includes(id)),
  );
  const [stepId, setStepId] = useState(available[0]?.id ?? steps[0]?.id ?? "");
  const step =
    steps.find((item) => item.id === stepId) ?? available[0] ?? steps[0];
  const upcoming = steps.find(
    (item) =>
      item.id !== step?.id && !project.completed_step_ids.includes(item.id),
  );
  const frame = project.frames.find(
    (item) => item.id === step?.reference_frame_id,
  );
  const [paused, setPaused] = useState(false);
  const [cloudConsent, setCloudConsent] = useState(false);
  const [voice, setVoice] = useState(false);
  const [check, setCheck] = useState<ScreenCheck | null>(null);
  const [redactions, setRedactions] = useState<Redaction[]>([]);
  const [redacting, setRedacting] = useState(false);
  const [draft, setDraft] = useState<Redaction | null>(null);
  const dragStart = useRef<{ x: number; y: number } | null>(null);
  const [manualBusy, setManualBusy] = useState(false);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [answer, setAnswer] = useState<{
    answer: string;
    evidence: string[];
    warnings: string[];
    provider_mode: string;
  } | null>(null);
  const upload = useRef<HTMLInputElement>(null);
  const lastSpoken = useRef({ key: "", at: 0 });
  const mounted = useRef(true);
  const manualAbort = useRef<AbortController | null>(null);
  const askAbort = useRef<AbortController | null>(null);
  const askGeneration = useRef(0);
  const invalidateAsk = useCallback(() => {
    askGeneration.current++;
    askAbort.current?.abort();
    if (mounted.current) setAsking(false);
  }, []);
  const canAnalyze =
    !!project.approved && !!step && (provider?.mode !== "meta" || cloudConsent);
  const cancelVoice = useCallback(() => {
    window.speechSynthesis?.cancel();
  }, []);
  const clearSession = useCallback(() => {
    manualAbort.current?.abort();
    invalidateAsk();
    cancelVoice();
    if (mounted.current) {
      setCheck(null);
      setAnswer(null);
      setRedactions([]);
      setCloudConsent(false);
      setPaused(false);
    }
    void api.clearScreenSession(project.id).catch(() => {});
  }, [project.id, cancelVoice, invalidateAsk]);
  async function analyze(blob: Blob, signal: AbortSignal, source: string) {
    if (!step) return;
    const value = await api.screenCheck(
      project.id,
      step.id,
      blob,
      cloudConsent,
      "",
      source,
      signal,
    );
    if (signal.aborted || !mounted.current) return;
    setCheck(value);
    onUpdate({ ...project, completed_step_ids: value.completed_step_ids });
    if (value.result.status === "pass" && value.current_step_id)
      setStepId(value.current_step_id);
  }
  const screen = useScreenCapture({
    projectId: project.id,
    enabled: canAnalyze,
    paused: paused || redacting,
    interval: provider?.mode === "meta" ? 12000 : 4000,
    redactions,
    onCapture: analyze,
    onStop: clearSession,
    onError,
  });
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      manualAbort.current?.abort();
      invalidateAsk();
      cancelVoice();
    };
  }, [cancelVoice, invalidateAsk]);
  useEffect(() => {
    setCloudConsent(false);
    invalidateAsk();
    setAnswer(null);
  }, [project.id, provider?.mode, invalidateAsk]);
  useEffect(() => {
    if (paused || !voice || redacting) cancelVoice();
  }, [paused, voice, redacting, cancelVoice]);
  useEffect(() => {
    if (!voice || paused || redacting || !check || !window.speechSynthesis)
      return;
    const key = JSON.stringify({
      step: check.result.step_id,
      status: check.result.status,
      reason: check.result.reason,
      explanation: check.result.explanation,
      corrections: check.result.rule_results
        .map((rule) => rule.correction)
        .filter(Boolean),
    });
    if (
      lastSpoken.current.key === key ||
      Date.now() - lastSpoken.current.at < 10000
    )
      return;
    lastSpoken.current = { key, at: Date.now() };
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(
      new SpeechSynthesisUtterance(check.result.explanation),
    );
  }, [check, voice, paused, redacting]);

  async function manual(file?: File) {
    if (!file || !canAnalyze || manualBusy) return;
    if (
      !/^image\/(png|jpeg|webp)$/.test(file.type) ||
      file.size > 10 * 1024 * 1024
    ) {
      onError("Choose a JPEG, PNG, or WebP screenshot up to 10 MB.");
      return;
    }
    setManualBusy(true);
    setPaused(true);
    cancelVoice();
    const controller = new AbortController();
    manualAbort.current = controller;
    try {
      await analyze(file, controller.signal, "manually selected screenshot");
    } catch (error) {
      if (!controller.signal.aborted && mounted.current)
        onError((error as Error).message);
    } finally {
      if (mounted.current) setManualBusy(false);
    }
  }
  async function ask() {
    if (!question.trim()) return;
    askAbort.current?.abort();
    const controller = new AbortController();
    askAbort.current = controller;
    const generation = ++askGeneration.current;
    setAsking(true);
    try {
      const value = await api.ask(
        project.id,
        question.trim(),
        controller.signal,
      );
      if (
        mounted.current &&
        !controller.signal.aborted &&
        generation === askGeneration.current
      )
        setAnswer(value);
    } catch (error) {
      if (
        mounted.current &&
        !controller.signal.aborted &&
        generation === askGeneration.current
      )
        onError((error as Error).message);
    } finally {
      if (mounted.current && generation === askGeneration.current)
        setAsking(false);
    }
  }
  function next() {
    const candidate = available.find((item) => item.id !== step?.id);
    if (candidate) setStepId(candidate.id);
    else
      onError(
        "No other eligible checkpoint is unlocked. Verify the current step before continuing.",
      );
  }
  function point(event: React.PointerEvent<HTMLDivElement>) {
    const rect = event.currentTarget.getBoundingClientRect();
    return {
      x: Math.max(0, Math.min(1, (event.clientX - rect.left) / rect.width)),
      y: Math.max(0, Math.min(1, (event.clientY - rect.top) / rect.height)),
    };
  }
  if (!project.task || !project.approved)
    return (
      <div className="panel">
        <Empty
          icon={<ShieldCheck size={28} />}
          title="Review the digital workflow first."
        >
          <p>
            Confirm the expected UI states and screen rules before screen
            observation.
          </p>
          <button className="button primary" onClick={onReview}>
            Review workflow
            <ArrowRight size={16} />
          </button>
        </Empty>
      </div>
    );
  return (
    <div className="screen-assistant page-enter">
      {steps.length > 0 && available.length === 0 && (
        <div className="approval-banner approved">
          <ShieldCheck size={23} />
          <div>
            <strong>All digital checkpoints are verified.</strong>
            <p>
              Your workflow is complete. Stop sharing to clear the screen
              session.
            </p>
          </div>
        </div>
      )}
      <div className="screen-privacy-banner">
        <ShieldCheck size={20} />
        <div>
          <strong>Your window. Your control.</strong>
          <p>
            Choose a separate workflow tab or window. Screenshots are processed
            in memory and discarded; no click automation or filesystem access.
          </p>
        </div>
        <Badge variant="cyan">
          {provider?.mode === "meta" ? "META · LIVE UNVERIFIED" : "LOCAL OCR"}
        </Badge>
      </div>
      <div className="screen-layout">
        <section className="screen-main">
          <section className="panel">
            <div className="panel-heading">
              <h2>
                <Monitor size={18} />
                Live screen assistant
              </h2>
              <Badge variant={screen.sharing ? "pass" : "neutral"}>
                {screen.sharing
                  ? paused || redacting
                    ? "SHARING · PAUSED"
                    : "SHARING"
                  : "NOT SHARING"}
              </Badge>
            </div>
            <div
              className={`screen-preview ${redacting ? "redacting" : ""}`}
              onPointerDown={(event) => {
                if (!redacting || !screen.sharing) return;
                event.currentTarget.setPointerCapture(event.pointerId);
                dragStart.current = point(event);
              }}
              onPointerMove={(event) => {
                if (!dragStart.current) return;
                const p = point(event);
                setDraft({
                  x: Math.min(p.x, dragStart.current.x),
                  y: Math.min(p.y, dragStart.current.y),
                  width: Math.abs(p.x - dragStart.current.x),
                  height: Math.abs(p.y - dragStart.current.y),
                });
              }}
              onPointerUp={() => {
                if (draft && draft.width > 0.005 && draft.height > 0.005)
                  setRedactions((prev) => [...prev, draft]);
                dragStart.current = null;
                setDraft(null);
              }}
            >
              <video
                ref={screen.videoRef}
                autoPlay
                muted
                playsInline
                aria-label="Shared screen preview"
                className={screen.sharing ? "" : "hidden-preview"}
                onLoadedData={() => void screen.capture(true)}
              />
              {!screen.sharing && (
                <div className="screen-empty">
                  <Monitor size={35} />
                  <h2>Bring your workflow into view.</h2>
                  <p>
                    Share a browser tab or application window.
                    <br />
                    ReplayLab reads the visible UI, never hidden state.
                  </p>
                  <button
                    className="button primary"
                    disabled={screen.starting || !canAnalyze}
                    onClick={() => void screen.start()}
                  >
                    {screen.starting ? (
                      <Spinner label="Waiting for screen selection…" />
                    ) : (
                      <>
                        <Monitor size={16} />
                        Choose screen or window
                      </>
                    )}
                  </button>
                  <small>
                    {provider?.mode === "meta"
                      ? "Cloud consent is required before analysis."
                      : "Your selection authorizes processing by local OCR. No Meta calls in offline mode."}
                  </small>
                </div>
              )}
              {screen.sharing &&
                [...redactions, ...(draft ? [draft] : [])].map((box, i) => (
                  <div
                    key={i}
                    className="screen-redaction"
                    style={{
                      left: `${box.x * 100}%`,
                      top: `${box.y * 100}%`,
                      width: `${box.width * 100}%`,
                      height: `${box.height * 100}%`,
                    }}
                  >
                    <EyeOff size={15} />
                  </div>
                ))}
            </div>
            <div className="screen-scope">
              <span>
                {screen.sharing
                  ? `Visible capture scope: ${screen.scope}`
                  : "Capture starts only after your explicit browser selection."}
              </span>
              <span>
                {screen.analyzing || manualBusy ? (
                  <Spinner label="Reading screen…" />
                ) : (
                  `${screen.skipped} unchanged frames skipped`
                )}
              </span>
            </div>
            <div className="screen-controls">
              <button
                className="button secondary compact"
                disabled={!screen.sharing}
                onClick={() => {
                  setPaused(!paused);
                  cancelVoice();
                }}
              >
                {paused ? <Play size={14} /> : <Pause size={14} />}
                {paused ? "Resume" : "Pause"}
              </button>
              <button
                className="button secondary compact"
                disabled={
                  !screen.sharing || screen.analyzing || !canAnalyze || paused
                }
                onClick={() => void screen.capture(true)}
              >
                <RefreshCw size={14} />
                Recheck
              </button>
              <button
                className="button secondary compact"
                disabled={!screen.sharing && !screen.starting}
                onClick={screen.stop}
              >
                <Square size={13} />
                Stop sharing
              </button>
              <button
                className="button secondary compact"
                disabled={!canAnalyze || manualBusy || screen.analyzing}
                onClick={() => upload.current?.click()}
              >
                <Upload size={14} />
                Upload screenshot
              </button>
              <input
                ref={upload}
                className="visually-hidden"
                type="file"
                accept="image/png,image/jpeg,image/webp"
                aria-label="Upload screen screenshot"
                onChange={(e) => {
                  void manual(e.target.files?.[0]);
                  e.target.value = "";
                }}
              />
              <button
                className="icon-button"
                aria-label={
                  voice ? "Mute voice guidance" : "Enable voice guidance"
                }
                disabled={!window.speechSynthesis}
                onClick={() => {
                  setVoice(!voice);
                  cancelVoice();
                }}
              >
                {voice ? <Volume2 size={17} /> : <VolumeX size={17} />}
              </button>
            </div>
            <div className="screen-redaction-controls">
              <button
                className={`button text-button compact ${redacting ? "selected" : ""}`}
                disabled={!screen.sharing}
                onClick={() => setRedacting(!redacting)}
              >
                <EyeOff size={14} />
                {redacting ? "Done drawing masks" : "Redact private regions"}
              </button>
              {redactions.length > 0 && (
                <button
                  className="button text-button compact"
                  onClick={() => setRedactions([])}
                >
                  Clear {redactions.length} masks
                  <X size={12} />
                </button>
              )}
              <span>
                {redacting
                  ? "Analysis paused. Drag over sensitive regions; black masks are applied before sending pixels."
                  : "Masks are fixed to screen coordinates; update them when the layout changes. Manually selected screenshots are sent as selected."}
              </span>
            </div>
          </section>
          {provider?.mode === "meta" && (
            <label className="checkbox-row screen-cloud-consent">
              <input
                type="checkbox"
                checked={cloudConsent}
                onChange={(e) => setCloudConsent(e.target.checked)}
              />
              <span>
                I consent to sending this project’s redacted screen frames to
                Meta with store:false requested. Provider processing and
                retention terms apply; local screenshots are not retained. This
                choice resets when leaving the project or switching providers.
              </span>
            </label>
          )}
          {check && (
            <section
              className={`panel screen-result ${check.result.status}`}
              aria-label="Screen verification result"
            >
              <div className="result-heading">
                <div>
                  <VerdictBadge status={check.result.status} />
                  <Badge>
                    {check.result.provider_mode === "local_ocr"
                      ? "LOCAL OCR · REAL SCREEN PIXELS"
                      : check.result.provider_mode.toUpperCase()}
                  </Badge>
                </div>
                <h2>
                  {steps.find((item) => item.id === check.result.step_id)
                    ?.title ?? "Checkpoint evidence"}
                </h2>
                <p>{check.result.explanation}</p>
                {check.result.reason && (
                  <span className="screen-reason">
                    {check.result.reason.replaceAll("_", " ")}
                  </span>
                )}
              </div>
              <div className="screen-rule-results">
                {check.result.rule_results.map((rule) => (
                  <div key={rule.rule_id}>
                    <VerdictBadge status={rule.status} />
                    <div>
                      <p>
                        <strong>Expected:</strong> {rule.expected}
                      </p>
                      <p>
                        <strong>Observed:</strong> {rule.observed}
                      </p>
                      {rule.correction && (
                        <p className="rule-correction">{rule.correction}</p>
                      )}
                      {rule.evidence.map((evidence, i) => (
                        <small key={i}>{evidence}</small>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
              {check.result.warnings.map((warning, i) => (
                <p className="screen-warning" key={i}>
                  {warning}
                </p>
              ))}
              <details className="screen-observation-details">
                <summary>
                  Visible UI evidence · {check.observation.elements.length}{" "}
                  elements
                </summary>
                <pre>
                  {check.observation.visible_text ||
                    "No readable visible text."}
                </pre>
                <p>
                  Evidence source: {check.observation.provider_mode} ·
                  Screenshots stored: {check.screen_stored ? "yes" : "no"}
                </p>
                <p>
                  OCR confidence describes recognized characters; it is not a
                  probability of task completion.
                </p>
              </details>
            </section>
          )}
          <section className="panel screen-ask">
            <div className="panel-heading">
              <h2>
                <MessageSquare size={16} />
                Ask ReplayLab
              </h2>
              <Badge>WORKFLOW + OBSERVED EVIDENCE</Badge>
            </div>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                void ask();
              }}
            >
              <input
                aria-label="Ask about the current workflow"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                maxLength={1000}
                placeholder="What should I do next?"
              />
              <button
                className="button secondary"
                aria-label="Send question"
                disabled={asking || !question.trim()}
              >
                {asking ? <Spinner /> : <Send size={15} />}
              </button>
            </form>
            {answer && (
              <div className="screen-answer">
                <p>{answer.answer}</p>
                {answer.evidence.map((item, i) => (
                  <small key={i}>{item}</small>
                ))}
                {answer.warnings.map((item, i) => (
                  <p className="screen-warning" key={i}>
                    {item}
                  </p>
                ))}
                <Badge>{answer.provider_mode}</Badge>
              </div>
            )}
          </section>
        </section>
        <aside className="screen-guidance">
          <section className="panel">
            <div className="panel-heading">
              <h2>Current checkpoint</h2>
              <Badge>
                {steps.indexOf(step) + 1} / {steps.length}
              </Badge>
            </div>
            <div className="screen-step-copy">
              <h2>{step?.title ?? "Workflow complete"}</h2>
              <p>{step?.description}</p>
              {step?.expected_state && (
                <div className="screen-expected">
                  <strong>Expected visible state</strong>
                  <p>{step.expected_state}</p>
                </div>
              )}
              {frame && (
                <>
                  <EvidenceImage
                    src={frame.url}
                    alt={`Reference screenshot for ${step?.title}`}
                  />
                  <small>
                    Source reference · synthetic for the CodeLab demo
                  </small>
                </>
              )}
              <div className="screen-upcoming">
                <span className="eyebrow">UP NEXT</span>
                <strong>{upcoming?.title ?? "All checkpoints verified"}</strong>
              </div>
              <button className="button secondary full-width" onClick={next}>
                Next eligible step
                <ArrowRight size={14} />
              </button>
              <small>
                Manual navigation never marks a checkpoint complete.
              </small>
            </div>
          </section>
          <section className="panel screen-setup">
            <h3>Reproducible digital demo</h3>
            <p>
              Open the CodeLab sandbox, then share that separate tab or window.
              Keep this coaching screen out of the capture.
            </p>
            <a
              className="button secondary full-width"
              href="?digital-demo=1"
              target="_blank"
              rel="noopener noreferrer"
            >
              Open CodeLab sandbox
              <ExternalLink size={14} />
            </a>
            <p>
              Interface versions are read from visible screen pixels, never
              inferred from a manually supplied label.
            </p>
            <p>
              Local OCR reads actual pixels. Workflow extraction in offline mode
              uses clearly labeled templates. Unsupported or unclear screens
              remain UNCERTAIN.
            </p>
          </section>
        </aside>
      </div>
    </div>
  );
}
