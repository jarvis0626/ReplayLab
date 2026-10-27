import { useState } from "react";
import { ArrowRight, FileText, Link, ShieldCheck } from "lucide-react";
import type { Project } from "../types";
import { api } from "../services/api";
import { Badge, formatTime, Spinner } from "./ui";

export function TutorialSource({
  project,
  onUpdate,
  onError,
}: {
  project: Project;
  onUpdate: (project: Project) => void;
  onError: (message: string) => void;
}) {
  const [url, setUrl] = useState("");
  const [transcript, setTranscript] = useState("");
  const [title, setTitle] = useState("");
  const [rights, setRights] = useState(false);
  const [busy, setBusy] = useState(false);
  async function save() {
    setBusy(true);
    try {
      onUpdate(
        await api.tutorial(project.id, {
          ...(url.trim() ? { youtube_url: url.trim() } : {}),
          ...(transcript.trim() ? { transcript: transcript.trim() } : {}),
          ...(title.trim() ? { title: title.trim() } : {}),
          usage_rights_confirmed: rights,
        }),
      );
    } catch (error) {
      onError((error as Error).message);
    } finally {
      setBusy(false);
    }
  }
  let embed: string | null = null;
  if (project.tutorial?.embed_url) {
    try {
      const parsed = new URL(project.tutorial.embed_url);
      if (
        ["www.youtube-nocookie.com", "www.youtube.com"].includes(
          parsed.hostname,
        ) &&
        parsed.protocol === "https:" &&
        /^\/embed\/[a-zA-Z0-9_-]{11}$/.test(parsed.pathname)
      )
        embed = parsed.toString();
    } catch {
      /* reject untrusted embed URLs */
    }
  }
  return (
    <section className="panel tutorial-source">
      <div className="panel-heading">
        <div>
          <h2>
            <FileText size={17} />
            Tutorial source
          </h2>
          <p>
            Upload a tutorial above, or add a reference URL and a timestamped
            transcript.
          </p>
        </div>
        <Badge>DIGITAL WORKFLOW</Badge>
      </div>
      <div className="tutorial-body">
        {project.tutorial?.instruction_warnings?.map((warning, i) => (
          <div className="screen-warning" key={i}>
            {warning}
          </div>
        ))}
        {embed && (
          <iframe
            title="YouTube tutorial reference"
            src={embed}
            referrerPolicy="strict-origin-when-cross-origin"
            sandbox="allow-scripts allow-same-origin allow-presentation"
            allow="encrypted-media; picture-in-picture"
            allowFullScreen
          />
        )}
        <label>
          Tutorial title (optional)
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Install Replay Formatter in CodeLab"
            maxLength={240}
          />
        </label>
        <label>
          <Link size={13} />
          YouTube reference URL (optional)
          <input
            type="url"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://www.youtube.com/watch?v=…"
          />
        </label>
        <label>
          Timestamped transcript
          <textarea
            rows={6}
            value={transcript}
            onChange={(e) => setTranscript(e.target.value)}
            placeholder={
              "00:00 Open the Extensions panel.\n00:04 Search for Replay Formatter.\n00:08 Open its details.\n00:12 Select Install extension and confirm Enabled."
            }
            maxLength={100000}
          />
        </label>
        <div className="info-note">
          <ShieldCheck size={16} />
          <span>
            YouTube links are embedded references only. ReplayLab never
            downloads videos or scrapes captions. Paste a transcript you have
            permission to use; a URL alone does not supply tutorial steps.
          </span>
        </div>
        <label className="checkbox-row">
          <input
            type="checkbox"
            checked={rights}
            onChange={(e) => setRights(e.target.checked)}
          />
          <span>
            I have permission to use this tutorial/transcript and have reviewed
            its usage rights.
          </span>
        </label>
        <button
          className="button secondary"
          onClick={() => void save()}
          disabled={
            busy ||
            !rights ||
            (!url.trim() && !transcript.trim()) ||
            project.status === "processing"
          }
        >
          {busy ? (
            <Spinner label="Saving tutorial…" />
          ) : (
            <>
              Save tutorial source
              <ArrowRight size={15} />
            </>
          )}
        </button>
        {project.tutorial && (
          <div className="tutorial-segments">
            <h3>{project.tutorial.title}</h3>
            <Badge variant="neutral">
              {project.tutorial.kind.toUpperCase()} SOURCE
            </Badge>
            {project.tutorial.transcript_segments.map((segment, index) => (
              <div key={index}>
                <span>{formatTime(segment.start)}</span>
                <p>{segment.text}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
