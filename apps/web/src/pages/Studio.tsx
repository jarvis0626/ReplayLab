import { useRef, useState } from "react";
import {
  ArrowRight,
  Check,
  Cloud,
  Film,
  Image,
  ScanLine,
  Upload,
  Video,
} from "lucide-react";
import type { Project, Provider } from "../types";
import { api } from "../services/api";
import { Badge, ErrorBanner, formatTime, Spinner } from "../components/ui";
import { TutorialSource } from "../components/TutorialSource";

interface Props {
  project: Project;
  provider?: Provider;
  consent: boolean;
  onUpdate: (p: Project) => void;
  onTask: () => void;
  onError: (message: string) => void;
}
export function Studio({
  project,
  provider,
  consent,
  onUpdate,
  onTask,
  onError,
}: Props) {
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [localError, setLocalError] = useState("");
  const [usageRights, setUsageRights] = useState(false);
  const digital = project.modality === "digital";
  const [selectedFrame, setSelectedFrame] = useState(
    project.frames[0]?.id ?? "",
  );
  const input = useRef<HTMLInputElement>(null);
  const video = useRef<HTMLVideoElement>(null);
  async function upload(file?: File) {
    if (!file) return;
    if (digital && !usageRights) {
      setLocalError(
        "Confirm your usage rights before uploading a digital tutorial.",
      );
      return;
    }
    setLocalError("");
    if (!/\.(mp4|mov|webm|avi)$/i.test(file.name)) {
      setLocalError("Choose an MP4, MOV, WebM, or AVI video.");
      return;
    }
    if (file.size > 100 * 1024 * 1024) {
      setLocalError("This video is too large. Maximum upload size is 100 MB.");
      return;
    }
    setBusy(true);
    try {
      onUpdate(await api.uploadVideo(project.id, file, usageRights));
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function extract() {
    setBusy(true);
    try {
      onUpdate(await api.extract(project.id, consent));
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="studio-layout page-enter">
      <div className="studio-main">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>
                <Video size={17} />
                Demonstration studio
              </h2>
              <p>One clear view. One repeatable task.</p>
            </div>
            {project.video && (
              <Badge variant="neutral">
                {project.video.width} × {project.video.height}
              </Badge>
            )}
          </div>
          {localError && (
            <ErrorBanner
              message={localError}
              dismiss={() => setLocalError("")}
            />
          )}
          {digital && (
            <label className="checkbox-row tutorial-upload-rights">
              <input
                type="checkbox"
                checked={usageRights}
                onChange={(e) => setUsageRights(e.target.checked)}
              />
              <span>
                I have permission to upload and use this tutorial video.
              </span>
            </label>
          )}
          {project.video ? (
            <div className="video-player">
              <video
                ref={video}
                src={project.video.url}
                controls
                preload="metadata"
                aria-label="Demonstration video"
              />
              <div className="video-caption">
                <span>
                  <Film size={14} />
                  {project.video.original_name}
                </span>
                <span>{formatTime(project.video.duration)}</span>
              </div>
            </div>
          ) : (
            <button
              className={`upload-zone ${dragging ? "dragging" : ""}`}
              disabled={
                busy ||
                project.status === "processing" ||
                (digital && !usageRights)
              }
              onClick={() => input.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                void upload(e.dataTransfer.files[0]);
              }}
            >
              <span className="upload-icon">
                <Upload size={27} />
              </span>
              <h3>Drop a demonstration here</h3>
              <p>
                or <span>browse your files</span>
              </p>
              <small>MP4, MOV, WebM, AVI · Up to 100 MB · 2 minutes max</small>
            </button>
          )}
          <input
            className="visually-hidden"
            ref={input}
            type="file"
            accept="video/mp4,video/quicktime,video/webm,video/x-msvideo,.avi"
            aria-label="Upload demonstration video"
            onChange={(e) => {
              void upload(e.target.files?.[0]);
              e.target.value = "";
            }}
          />
          <div className="studio-actionbar">
            <span className="muted">
              {busy ? (
                <Spinner label="Uploading / processing…" />
              ) : project.status === "processing" ? (
                <Spinner label="Processing your demonstration…" />
              ) : (
                <>
                  <Check size={14} />
                  Files are validated on the server
                </>
              )}
            </span>
            {project.video && (
              <button
                className="button secondary compact"
                disabled={busy || project.status === "processing"}
                onClick={() => input.current?.click()}
              >
                Replace video
              </button>
            )}
          </div>
        </section>
        {digital && (
          <TutorialSource
            project={project}
            onUpdate={onUpdate}
            onError={onError}
          />
        )}
        <section className="panel keyframe-panel">
          <div className="panel-heading">
            <div>
              <h2>
                <Image size={17} />
                Source evidence
              </h2>
              <p>{project.tutorial?.kind === "demo" ? "Authored source references used to create this controlled demo video." : "Real frames extracted from your demonstration."}</p>
            </div>
            <Badge>{project.frames.length} frames</Badge>
          </div>
          {project.frames.length ? (
            <div className="keyframe-strip">
              {project.frames.map((frame) => (
                <button
                  key={frame.id}
                  className={`keyframe ${selectedFrame === frame.id ? "selected" : ""}`}
                  onClick={() => {
                    setSelectedFrame(frame.id);
                    if (video.current)
                      video.current.currentTime = frame.timestamp;
                  }}
                >
                  <img
                    src={frame.url}
                    alt={`Reference frame at ${formatTime(frame.timestamp)}`}
                  />
                  <span>{formatTime(frame.timestamp)}</span>
                </button>
              ))}
            </div>
          ) : (
            <div className="frame-empty">
              <ScanLine size={24} />
              <p>Keyframes appear after your video is processed.</p>
            </div>
          )}
        </section>
      </div>
      <aside className="studio-aside">
        <section className="panel instruction-panel">
          <span className="eyebrow">FROM VIDEO TO TASK</span>
          <h2>A little clarity goes a long way.</h2>
          <p className="muted">
            {digital ? "Use a tutorial with readable interface labels and clearly visible checkpoints." : "This research preview is built for a four-step colored-block assembly."}
          </p>
          <ol className="numbered-tips">
            <li>
              <span>01</span>
              <div>
                <strong>{digital ? "Show the application clearly" : "Keep the camera steady"}</strong>
                <p>
                  {digital ? "Record only the relevant app and keep its text readable." : "Use the same tabletop angle for demonstration and practice."}
                </p>
              </div>
            </li>
            <li>
              <span>02</span>
              <div>
                <strong>{digital ? "Name observable UI states" : "Show every component"}</strong>
                <p>{digital ? "Use a timestamped transcript with quoted labels to support offline extraction." : "Keep colors distinct and avoid covering the blocks."}</p>
              </div>
            </li>
            <li>
              <span>03</span>
              <div>
                <strong>Pause between actions</strong>
                <p>Make each completed state clearly visible.</p>
              </div>
            </li>
          </ol>
        </section>
        <section className="panel extraction-panel">
          <div className="row-between">
            <span className="panel-icon">
              <ScanLine size={20} />
            </span>
            <Badge variant={provider?.mode === "mock" ? "mock" : "cyan"}>
              {provider?.mode === "mock"
                ? "MOCK EXTRACTION"
                : "META EXTRACTION"}
            </Badge>
          </div>
          <h3>Understand the task</h3>
          <p>
            {provider?.mode === "mock"
              ? digital
                ? "Create an editable workflow using the labeled CodeLab template or supplied transcript. Offline extraction is not Muse Spark inference; review every visible UI rule."
                : "Generate the labeled four-step sample structure. Your video supplies real frames; offline steps are fixed demonstration instructions."
              : "Send the demonstration to the configured Meta reasoner to propose structured steps and observable rules."}
          </p>
          {provider?.mode === "meta" && !consent && (
            <div className="info-note">
              <Cloud size={16} />
              <span>
                Enable cloud-processing consent in provider settings before
                extraction.
              </span>
            </div>
          )}
          <button
            className="button primary full-width"
            disabled={
              (!project.video && !(digital && project.tutorial)) ||
              busy ||
              project.status === "processing" ||
              (provider?.mode === "meta" && !consent)
            }
            onClick={() => void extract()}
          >
            {project.status === "processing" ? (
              <Spinner label="Extracting task…" />
            ) : (
              <>
                Generate task steps
                <ArrowRight size={16} />
              </>
            )}
          </button>
          {project.task && (
            <button className="button secondary full-width" onClick={onTask}>
              Review task & graph
              <ArrowRight size={16} />
            </button>
          )}
          <small>Proposed steps always require your review and approval.</small>
        </section>
      </aside>
    </div>
  );
}
