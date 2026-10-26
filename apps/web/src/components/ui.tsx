import {
  AlertCircle,
  CheckCircle2,
  CircleHelp,
  LoaderCircle,
  X,
  XCircle,
} from "lucide-react";
import type { ReactNode } from "react";
import type { Observation, Verdict } from "../types";

export function Badge({
  children,
  variant = "",
}: {
  children: ReactNode;
  variant?: string;
}) {
  return <span className={`badge ${variant}`}>{children}</span>;
}
export function Spinner({ label = "Working…" }: { label?: string }) {
  return (
    <span className="loading-inline">
      <LoaderCircle className="spin" size={17} />
      {label}
    </span>
  );
}
export function Empty({
  icon,
  title,
  children,
}: {
  icon: ReactNode;
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="empty-state">
      <div className="empty-icon">{icon}</div>
      <h3>{title}</h3>
      <div className="muted">{children}</div>
    </div>
  );
}
export function ErrorBanner({
  message,
  dismiss,
}: {
  message: string;
  dismiss?: () => void;
}) {
  return (
    <div className="error-banner" role="alert">
      <AlertCircle size={19} />
      <span>{message}</span>
      {dismiss && (
        <button
          className="icon-button"
          onClick={dismiss}
          aria-label="Dismiss error"
        >
          <X size={16} />
        </button>
      )}
    </div>
  );
}
export function VerdictBadge({ status }: { status: Verdict }) {
  const Icon =
    status === "pass" ? CheckCircle2 : status === "fail" ? XCircle : CircleHelp;
  return (
    <Badge variant={status}>
      <Icon size={14} />
      {status.toUpperCase()}
    </Badge>
  );
}
export function EvidenceImage({
  src,
  alt,
  observations = [],
  className = "",
}: {
  src: string;
  alt: string;
  observations?: Observation[];
  className?: string;
}) {
  return (
    <div className={`evidence-image ${className}`}>
      <img src={src} alt={alt} />
      {observations
        .filter((o) => o.bbox?.length === 4)
        .map((o, i) => (
          <div
            className="observation-box"
            key={`${o.label}-${i}`}
            style={{
              left: `${o.bbox[0] * 100}%`,
              top: `${o.bbox[1] * 100}%`,
              width: `${(o.bbox[2] - o.bbox[0]) * 100}%`,
              height: `${(o.bbox[3] - o.bbox[1]) * 100}%`,
            }}
          >
            <span>
              {o.label}
              {o.confidence !== null
                ? ` · ${Math.round(o.confidence * 100)}%`
                : ""}
            </span>
          </div>
        ))}
    </div>
  );
}
export function formatTime(value: number) {
  const tenths = Math.max(0, Math.round(value * 10));
  const seconds = Math.floor((tenths % 600) / 10)
    .toString()
    .padStart(2, "0");
  return `${Math.floor(tenths / 600)}:${seconds}.${tenths % 10}`;
}
