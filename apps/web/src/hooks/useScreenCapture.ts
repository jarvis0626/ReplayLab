import { useCallback, useEffect, useRef, useState } from "react";

export interface Redaction {
  x: number;
  y: number;
  width: number;
  height: number;
}
interface Options {
  projectId: string;
  enabled: boolean;
  paused: boolean;
  interval: number;
  redactions: Redaction[];
  onCapture: (blob: Blob, signal: AbortSignal, scope: string) => Promise<void>;
  onStop: () => void;
  onError: (message: string) => void;
}

export function useScreenCapture(options: Options) {
  const latest = useRef(options);
  latest.current = options;
  const [sharing, setSharing] = useState(false);
  const [starting, setStarting] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [scope, setScope] = useState("");
  const [skipped, setSkipped] = useState(0);
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const generation = useRef(0);
  const active = useRef(true);
  const pending = useRef(false);
  const abort = useRef<AbortController | null>(null);
  const fingerprint = useRef<Uint8ClampedArray | null>(null);
  const scopeRef = useRef("");

  const stop = useCallback(() => {
    generation.current++;
    abort.current?.abort();
    streamRef.current?.getTracks().forEach((track) => {
      track.onended = null;
      track.stop();
    });
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    fingerprint.current = null;
    pending.current = false;
    if (active.current) {
      setSharing(false);
      setStarting(false);
      setAnalyzing(false);
      setScope("");
    }
    latest.current.onStop();
  }, []);

  useEffect(() => {
    active.current = true;
    return () => {
      active.current = false;
      stop();
    };
  }, [options.projectId, stop]);
  useEffect(() => {
    if (options.paused || !options.enabled) abort.current?.abort();
  }, [options.paused, options.enabled]);
  useEffect(() => {
    if (!sharing || !videoRef.current || !streamRef.current) return;
    videoRef.current.srcObject = streamRef.current;
    void videoRef.current
      .play()
      .catch(() =>
        latest.current.onError(
          "The shared-screen preview could not play. Stop and select the window again.",
        ),
      );
  }, [sharing]);

  async function start() {
    if (starting || streamRef.current) return;
    if (!navigator.mediaDevices?.getDisplayMedia) {
      latest.current.onError(
        "Screen sharing requires a supported browser on localhost or HTTPS. You can upload a screenshot instead.",
      );
      return;
    }
    const token = ++generation.current;
    setStarting(true);
    try {
      const stream = await navigator.mediaDevices.getDisplayMedia({
        video: { frameRate: { ideal: 5, max: 10 } },
        audio: false,
      });
      if (!active.current || token !== generation.current) {
        stream.getTracks().forEach((track) => track.stop());
        return;
      }
      streamRef.current = stream;
      const track = stream.getVideoTracks()[0];
      const surface = (
        track?.getSettings() as MediaTrackSettings & { displaySurface?: string }
      )?.displaySurface;
      scopeRef.current =
        surface === "browser"
          ? "browser tab"
          : surface === "window"
            ? "application window"
            : surface === "monitor"
              ? "entire display"
              : "browser-selected surface (scope unavailable)";
      setScope(scopeRef.current);
      if (track) track.onended = stop;
      setSharing(true);
    } catch {
      if (active.current && token === generation.current)
        latest.current.onError(
          "Screen sharing was denied or canceled. Nothing was captured. Choose a browser tab or window when you are ready.",
        );
    } finally {
      if (active.current && token === generation.current) setStarting(false);
    }
  }

  const capture = useCallback(async (force = false) => {
    const opts = latest.current;
    if (
      !opts.enabled ||
      opts.paused ||
      pending.current ||
      !streamRef.current ||
      !videoRef.current?.videoWidth
    )
      return;
    const video = videoRef.current;
    const canvas = document.createElement("canvas");
    const scale = Math.min(1, 1600 / video.videoWidth);
    canvas.width = Math.max(1, Math.round(video.videoWidth * scale));
    canvas.height = Math.max(1, Math.round(video.videoHeight * scale));
    const context = canvas.getContext("2d", { willReadFrequently: true });
    if (!context) return;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    context.fillStyle = "#000000";
    for (const box of opts.redactions)
      context.fillRect(
        box.x * canvas.width,
        box.y * canvas.height,
        box.width * canvas.width,
        box.height * canvas.height,
      );
    const thumb = document.createElement("canvas");
    thumb.width = 160;
    thumb.height = 90;
    const thumbContext = thumb.getContext("2d", { willReadFrequently: true });
    if (!thumbContext) return;
    thumbContext.drawImage(canvas, 0, 0, 160, 90);
    const pixels = thumbContext.getImageData(0, 0, 160, 90).data;
    if (!force && fingerprint.current) {
      let changed = 0;
      for (let i = 0; i < pixels.length; i += 4)
        if (
          Math.abs(pixels[i] - fingerprint.current[i]) +
            Math.abs(pixels[i + 1] - fingerprint.current[i + 1]) +
            Math.abs(pixels[i + 2] - fingerprint.current[i + 2]) >
          20
        )
          changed++;
      if (changed < 8) {
        setSkipped((n) => n + 1);
        return;
      }
    }
    const token = generation.current;
    pending.current = true;
    setAnalyzing(true);
    const controller = new AbortController();
    abort.current = controller;
    try {
      const blob = await new Promise<Blob | null>((resolve) =>
        canvas.toBlob(resolve, "image/png"),
      );
      if (
        blob &&
        active.current &&
        token === generation.current &&
        !controller.signal.aborted
      ) {
        await opts.onCapture(blob, controller.signal, scopeRef.current);
        if (!controller.signal.aborted && token === generation.current)
          fingerprint.current = pixels.slice();
      }
    } catch (error) {
      if (
        !controller.signal.aborted &&
        active.current &&
        token === generation.current
      )
        latest.current.onError((error as Error).message);
    } finally {
      if (active.current && token === generation.current) {
        pending.current = false;
        setAnalyzing(false);
      }
    }
  }, []);
  useEffect(() => {
    if (!sharing || options.paused || !options.enabled) return;
    const timer = window.setInterval(() => void capture(), options.interval);
    return () => clearInterval(timer);
  }, [sharing, options.paused, options.enabled, options.interval, capture]);
  return {
    videoRef,
    sharing,
    starting,
    analyzing,
    scope,
    skipped,
    start,
    stop,
    capture,
  };
}
