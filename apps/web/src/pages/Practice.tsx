import { useEffect, useRef, useState } from "react";
import {
  ArrowRight,
  Camera,
  CameraOff,
  Check,
  CheckCircle2,
  ChevronDown,
  Cloud,
  ImagePlus,
  Layers3,
  RefreshCw,
  ScanLine,
  ShieldCheck,
  Upload,
} from "lucide-react";
import type {
  Attempt,
  Fixture,
  Project,
  Provider,
  VerificationResult,
  WorkflowVerification,
} from "../types";
import { api } from "../services/api";
import { EvidenceInspector, VerificationHistory } from "../components/EvidenceInspector";
import {
  Badge,
  Empty,
  EvidenceImage,
  Spinner,
  VerdictBadge,
} from "../components/ui";

interface Props {
  project: Project;
  provider?: Provider;
  consent: boolean;
  onUpdate: (p: Project) => void;
  onError: (message: string) => void;
  onReview: () => void;
}
export function Practice({
  project,
  provider,
  consent,
  onUpdate,
  onError,
  onReview,
}: Props) {
  const steps = project.task?.steps ?? [];
  const eligible = steps.filter(
    (s) =>
      !project.completed_step_ids.includes(s.id) &&
      s.dependencies.every((id) => project.completed_step_ids.includes(id)),
  );
  const [stepId, setStepId] = useState(eligible[0]?.id ?? steps[0]?.id ?? "");
  const step = steps.find((s) => s.id === stepId) ?? eligible[0] ?? steps[0];
  const frame = project.frames.find((f) => f.id === step?.reference_frame_id);
  const [fixtures, setFixtures] = useState<Fixture[]>([]);
  const [attempts, setAttempts] = useState<Attempt[]>([]);
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [busy, setBusy] = useState(false);
  const [cameraRunning, setCameraRunning] = useState(false);
  const [cameraStarting, setCameraStarting] = useState(false);
  const [cameraError, setCameraError] = useState("");
  const [showFixtures, setShowFixtures] = useState(false);
  const [comparable, setComparable] = useState<boolean | null>(null);
  const [visibilityConfirmed, setVisibilityConfirmed] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    void api
      .fixtures()
      .then(setFixtures)
      .catch((e: Error) => onError(e.message));
    void api
      .attempts(project.id)
      .then(setAttempts)
      .catch((e: Error) => onError(e.message));
    return () => {
      mounted.current = false;
      stream.current?.getTracks().forEach((track) => track.stop());
    };
  }, [project.id, onError]);
  useEffect(() => {
    if (cameraRunning && video.current && stream.current) {
      video.current.srcObject = stream.current;
      void video.current
        .play()
        .catch(() =>
          setCameraError(
            "Camera playback could not start. Try restarting your camera.",
          ),
        );
    }
  }, [cameraRunning]);
  function stopCamera() {
    stream.current?.getTracks().forEach((track) => track.stop());
    stream.current = null;
    setCameraRunning(false);
  }
  async function startCamera() {
    setCameraError("");
    if (!navigator.mediaDevices?.getUserMedia) {
      setCameraError(
        "Camera access requires a secure browser context (localhost or HTTPS). You can upload an image instead.",
      );
      return;
    }
    setCameraStarting(true);
    try {
      const media = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: { ideal: "environment" },
          width: { ideal: 1280 },
          height: { ideal: 720 },
        },
        audio: false,
      });
      if (!mounted.current) {
        media.getTracks().forEach((track) => track.stop());
        return;
      }
      stream.current = media;
      setCameraRunning(true);
    } catch {
      if (mounted.current)
        setCameraError(
          "Camera access was denied or no camera is available. Check browser permissions, or upload a checkpoint image.",
        );
    } finally {
      if (mounted.current) setCameraStarting(false);
    }
  }
  async function upload(file?: File) {
    if (!file || !step) return;
    if (!/^image\/(png|jpeg|webp)$/.test(file.type)) {
      onError("Choose a JPEG, PNG, or WebP checkpoint image.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      onError("Checkpoint images must be 10 MB or smaller.");
      return;
    }
    setBusy(true);
    try {
      const value = await api.uploadAttempt(project.id, step.id, file);
      setAttempt(value);
      setAttempts((prev) => [value, ...prev]);
      stopCamera();
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function capture() {
    const element = video.current;
    if (!element || !element.videoWidth) {
      setCameraError("Wait for the camera preview before capturing.");
      return;
    }
    const canvas = document.createElement("canvas");
    canvas.width = element.videoWidth;
    canvas.height = element.videoHeight;
    canvas.getContext("2d")?.drawImage(element, 0, 0);
    canvas.toBlob(
      (blob) => {
        if (blob)
          void upload(
            new File([blob], "checkpoint.jpg", { type: "image/jpeg" }),
          );
        else
          onError(
            "Could not capture a camera image. Please try an image upload.",
          );
      },
      "image/jpeg",
      0.92,
    );
  }
  async function useFixture(fixture: Fixture) {
    setBusy(true);
    try {
      const response = await fetch(fixture.url);
      if (!response.ok) throw new Error("Could not load this fixture image.");
      const blob = await response.blob();
      await upload(
        new File([blob], `${fixture.id}.png`, {
          type: blob.type || "image/png",
        }),
      );
      setShowFixtures(false);
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function verify() {
    if (!attempt) return;
    setBusy(true);
    try {
      const value = await api.verify(
        attempt.id,
        consent,
        comparable,
        visibilityConfirmed,
      );
      setAttempt(value);
      setAttempts((prev) => prev.map((a) => (a.id === value.id ? value : a)));
      onUpdate(await api.project(project.id));
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function selectStep(id: string) {
    setStepId(id);
    setAttempt(null);
    setComparable(null);
    setVisibilityConfirmed(false);
  }
  if (!project.task || !project.approved)
    return (
      <div className="panel">
        <Empty
          icon={<ShieldCheck size={28} />}
          title="Review first. Then learn by doing."
        >
          <p>
            Approve the proposed task and checkpoint rules before starting
            guided practice.
          </p>
          <button className="button primary" onClick={onReview}>
            Review task
            <ArrowRight size={16} />
          </button>
        </Empty>
      </div>
    );
  const complete =
    steps.length > 0 && project.completed_step_ids.length === steps.length;
  return (
    <div className="practice-page page-enter">
      {complete && (
        <div className="approval-banner approved">
          <CheckCircle2 size={25} />
          <div>
            <strong>Every checkpoint is verified.</strong>
            <p>
              Your approved task is complete. The evidence remains available in
              your attempt history.
            </p>
          </div>
          <Badge variant="pass">
            {steps.length} / {steps.length} COMPLETE
          </Badge>
        </div>
      )}
      <div className="practice-layout">
        <aside className="practice-steps panel">
          <div className="panel-heading">
            <h2>
              <Layers3 size={17} />
              Your practice
            </h2>
          </div>
          <div className="practice-step-list">
            {steps.map((s, i) => {
              const done = project.completed_step_ids.includes(s.id);
              const available =
                done ||
                s.dependencies.every((id) =>
                  project.completed_step_ids.includes(id),
                );
              return (
                <button
                  className={`practice-step ${s.id === step?.id ? "selected" : ""} ${done ? "done" : ""}`}
                  key={s.id}
                  disabled={!available}
                  onClick={() => selectStep(s.id)}
                >
                  <span>{done ? <Check size={15} /> : i + 1}</span>
                  <div>
                    <strong>{s.title}</strong>
                    <small>
                      {done
                        ? "Verified"
                        : available
                          ? "Ready to practice"
                          : "Complete prerequisites first"}
                    </small>
                  </div>
                </button>
              );
            })}
          </div>
          <div className="practice-side-note">
            <ShieldCheck size={18} />
            <p>
              Progress follows your action graph. A step unlocks when its
              prerequisites pass.
            </p>
          </div>
        </aside>
        <div className="practice-main">
          {step && (
            <>
              <div className="practice-instruction">
                <div className="row-between">
                  <span className="eyebrow">
                    CHECKPOINT {steps.indexOf(step) + 1} OF {steps.length}
                  </span>
                  <Badge variant={provider?.mode === "mock" ? "mock" : "cyan"}>
                    {provider?.mode === "mock"
                      ? "MOCK OBSERVATIONS"
                      : "META OBSERVATIONS"}
                  </Badge>
                </div>
                <h2>{step.title}</h2>
                <p>{step.description}</p>
                <div className="expected-rules">
                  {step.rules.map((rule) => (
                    <span key={rule.id}>
                      <ScanLine size={12} />
                      {rule.subject} {rule.kind}
                      {rule.target ? ` ${rule.target}` : ""}
                      {rule.value !== null && rule.value !== undefined
                        ? ` ${rule.value}`
                        : ""}
                    </span>
                  ))}
                </div>
              </div>
              <div className="comparison-grid">
                <section className="panel reference-panel">
                  <div className="panel-heading">
                    <h2>Reference state</h2>
                    <Badge>SOURCE EVIDENCE</Badge>
                  </div>
                  <div className="comparison-image">
                    {frame ? (
                      <EvidenceImage
                        src={frame.url}
                        alt={`Reference state for ${step.title}`}
                        observations={attempt?.reference_observations}
                      />
                    ) : (
                      <div className="camera-placeholder">
                        <ImagePlus size={28} />
                        <span>No reference frame selected</span>
                      </div>
                    )}
                  </div>
                  <div className="image-footer">
                    <span>Approved checkpoint</span>
                    <span>{step.rules.length} observable rules</span>
                  </div>
                </section>
                <section className="panel capture-panel">
                  <div className="panel-heading">
                    <h2>Your checkpoint</h2>
                    <Badge>
                      {attempt
                        ? "CAPTURED"
                        : cameraRunning
                          ? "CAMERA LIVE"
                          : "AWAITING IMAGE"}
                    </Badge>
                  </div>
                  <div className="comparison-image">
                    {attempt ? (
                      <EvidenceImage
                        src={attempt.image_url}
                        alt="Your checkpoint attempt"
                        observations={attempt.result?.observations}
                      />
                    ) : cameraRunning ? (
                      <video
                        className="webcam-preview"
                        ref={video}
                        autoPlay
                        muted
                        playsInline
                        aria-label="Live camera preview"
                      />
                    ) : (
                      <div className="camera-placeholder">
                        <Camera size={30} />
                        <strong>Show what you’ve built.</strong>
                        <span>Match the reference camera angle.</span>
                        <button
                          className="button secondary compact"
                          disabled={cameraStarting}
                          onClick={() => void startCamera()}
                        >
                          <Camera size={15} />
                          {cameraStarting ? "Starting camera?" : "Start camera"}
                        </button>
                        <small>
                          Your camera starts only when you request it.
                        </small>
                      </div>
                    )}
                  </div>
                  {cameraError && (
                    <p className="camera-error" role="alert">
                      {cameraError}
                    </p>
                  )}
                  <div className="capture-actions">
                    {cameraRunning && !attempt && (
                      <button
                        className="button primary compact"
                        onClick={capture}
                        disabled={busy}
                      >
                        <Camera size={15} />
                        Capture
                      </button>
                    )}
                    {cameraRunning && (
                      <button
                        className="icon-button"
                        onClick={stopCamera}
                        aria-label="Stop camera"
                      >
                        <CameraOff size={17} />
                      </button>
                    )}
                    {attempt && (
                      <button
                        className="button secondary compact"
                        disabled={busy}
                        onClick={() => setAttempt(null)}
                      >
                        <RefreshCw size={14} />
                        Retake
                      </button>
                    )}
                    <button
                      className="button secondary compact"
                      disabled={busy}
                      onClick={() => input.current?.click()}
                    >
                      <Upload size={14} />
                      Upload image
                    </button>
                    <input
                      type="file"
                      className="visually-hidden"
                      ref={input}
                      accept="image/png,image/jpeg,image/webp"
                      aria-label="Upload checkpoint image"
                      onChange={(e) => {
                        void upload(e.target.files?.[0]);
                        e.target.value = "";
                      }}
                    />
                  </div>
                </section>
              </div>
              {provider?.mode === "mock" && (
                <div className="fixture-note">
                  <div>
                    <Badge variant="mock">OFFLINE MODE</Badge>
                    <span>
                      Unrecognized uploaded images return UNCERTAIN. Labeled
                      fixtures provide known observations.
                    </span>
                  </div>
                  <button
                    className="button text-button compact"
                    onClick={() => setShowFixtures(!showFixtures)}
                  >
                    Load fixture
                    <ChevronDown size={14} />
                  </button>
                </div>
              )}
              {showFixtures && (
                <div className="fixture-grid">
                  {fixtures.map((fixture) => (
                    <button
                      className="fixture-card"
                      key={fixture.id}
                      onClick={() => void useFixture(fixture)}
                      disabled={busy}
                    >
                      <img src={fixture.url} alt={fixture.label} />
                      <strong>{fixture.label}</strong>
                      <small>{fixture.description}</small>
                    </button>
                  ))}
                </div>
              )}
              {attempt && !attempt.result && (
                <div className="verification-controls panel">
                  <div>
                    <label htmlFor="camera-comparability">
                      Camera comparability
                    </label>
                    <select
                      id="camera-comparability"
                      value={
                        comparable === null ? "auto" : comparable ? "yes" : "no"
                      }
                      onChange={(e) =>
                        setComparable(
                          e.target.value === "auto"
                            ? null
                            : e.target.value === "yes",
                        )
                      }
                    >
                      <option value="auto">Use available evidence</option>
                      <option value="yes">
                        I confirm the same camera angle
                      </option>
                      <option value="no">Camera view differs</option>
                    </select>
                  </div>
                  <div className="attestation-controls">
                    <label className="checkbox-row compact">
                      <input
                        type="checkbox"
                        checked={comparable === true}
                        onChange={(e) =>
                          setComparable(e.target.checked ? true : null)
                        }
                      />
                      <span>
                        Reference and checkpoint use a comparable camera view
                      </span>
                    </label>
                    <label className="checkbox-row compact">
                      <input
                        type="checkbox"
                        checked={visibilityConfirmed}
                        onChange={(e) =>
                          setVisibilityConfirmed(e.target.checked)
                        }
                      />
                      <span>
                        All required objects are visible in both images
                      </span>
                    </label>
                    <small className="muted">
                      These are your attestations, not model confidence. Missing
                      evidence still yields UNCERTAIN.
                    </small>
                  </div>
                  <button
                    className="button primary"
                    disabled={busy || (provider?.mode === "meta" && !consent)}
                    onClick={() => void verify()}
                  >
                    {busy ? (
                      <Spinner label="Verifying evidence…" />
                    ) : (
                      <>
                        <ScanLine size={17} />
                        Verify checkpoint
                      </>
                    )}
                  </button>
                  {provider?.mode === "meta" && !consent && (
                    <p className="consent-required">
                      <Cloud size={14} />
                      Cloud-processing consent is required in provider settings.
                    </p>
                  )}
                </div>
              )}
              {busy && !attempt && (
                <div className="loading-panel">
                  <Spinner label="Preparing checkpoint image…" />
                </div>
              )}
              {attempt?.result && (
                <VerificationPanel
                  result={attempt.result}
                  verification={attempt.verification}
                  onError={onError}
                  onRetry={() => setAttempt(null)}
                  onNext={
                    eligible.length && attempt.result.status === "pass"
                      ? () => selectStep(eligible[0].id)
                      : undefined
                  }
                />
              )}
              {attempts.length > 0 && (
                <section className="attempt-history">
                  <div className="section-heading">
                    <h3>Checkpoint history</h3>
                    <span className="muted small">
                      {attempts.length} attempt
                      {attempts.length !== 1 ? "s" : ""}
                    </span>
                  </div>
                  <div className="history-list">
                    {attempts
                      .filter((a) => a.step_id === step.id)
                      .map((a) => (
                        <button
                          key={a.id}
                          className={`history-item ${a.id === attempt?.id ? "selected" : ""}`}
                          onClick={() => setAttempt(a)}
                        >
                          <img src={a.image_url} alt="Previous checkpoint" />
                          <span>
                            {new Date(a.created_at).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                          {a.result ? (
                            <VerdictBadge status={a.result.status} />
                          ) : (
                            <Badge>Not verified</Badge>
                          )}
                        </button>
                      ))}
                  </div>
                </section>
              )}
              <VerificationHistory key={project.id} projectId={project.id} onError={onError} />
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export function VerificationPanel({
  result,
  onRetry,
  onNext,
  verification,
  onError,
}: {
  result: VerificationResult;
  onRetry: () => void;
  onNext?: () => void;
  verification?: WorkflowVerification | null;
  onError?: (message: string) => void;
}) {
  return (
    <section
      className={`verification-result panel ${result.status}`}
      aria-label="Verification result"
    >
      <div className="result-heading">
        <div>
          <VerdictBadge status={result.status} />
          <Badge variant={result.provider_mode === "mock" ? "mock" : "neutral"}>
            {result.provider_mode.toUpperCase()} OBSERVATIONS
          </Badge>
        </div>
        <h2>
          {result.status === "pass"
            ? "The visible requirements are satisfied."
            : result.status === "fail"
              ? "One checkpoint needs a correction."
              : "The evidence needs a clearer view."}
        </h2>
        <p>{result.explanation}</p>
      </div>
      <div className="result-diagnostics">
        <div>
          <h3>Rule-by-rule evidence</h3>
          <div className="rule-results">
            {result.rule_results.map((rule) => (
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
                  {rule.evidence.map((item, i) => (
                    <small key={i}>{item}</small>
                  ))}
                </div>
              </div>
            ))}
          </div>
          {!result.rule_results.length && (
            <p className="muted small">
              No adequately observed checkpoint constraints were available.
            </p>
          )}
        </div>
        <div>
          <h3>Object observations</h3>
          {result.observations.length ? (
            <div className="observation-list">
              {result.observations.map((o, i) => (
                <div key={`${o.label}-${i}`}>
                  <span>{o.label}</span>
                  <span>
                    {o.confidence === null
                      ? "Quality not supplied"
                      : `${Math.round(o.confidence * 100)}% detection confidence`}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="muted small">
              No reliable object observations. This image cannot establish
              completion.
            </p>
          )}
          {result.evidence.length > 0 && (
            <ul className="evidence-list">
              {result.evidence.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ul>
          )}
        </div>
      </div>
      <EvidenceInspector key={verification?.id} verification={verification} onError={onError} />
      <div className="result-actions">
        <span className="muted small">
          Deterministic verdict · explanations cannot change the outcome
        </span>
        <div>
          <button className="button secondary compact" onClick={onRetry}>
            <RefreshCw size={14} />
            Try another image
          </button>
          {onNext && (
            <button className="button primary compact" onClick={onNext}>
              Next checkpoint
              <ArrowRight size={14} />
            </button>
          )}
        </div>
      </div>
    </section>
  );
}
