import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { LiveScreenAssistant } from "../pages/LiveScreenAssistant";
import { CodeLabDemo } from "../pages/CodeLabDemo";
import { TutorialSource } from "../components/TutorialSource";
import { api } from "../services/api";
import type { Project, ScreenCheck } from "../types";

const project: Project = {
  id: "digital-1",
  name: "CodeLab workflow",
  modality: "digital",
  created_at: "2026-10-27T00:00:00Z",
  status: "ready",
  error: null,
  video: null,
  frames: [],
  approved: true,
  completed_step_ids: [],
  task: {
    id: "task-digital",
    modality: "digital",
    title: "Install a practice extension",
    description: "Controlled software simulation",
    objects: [],
    provider_mode: "mock",
    provenance: {},
    steps: [
      {
        id: "one",
        title: "Open the panel",
        description: "Choose Extensions.",
        dependencies: [],
        timestamp_start: 0,
        timestamp_end: 4,
        reference_frame_id: null,
        object_labels: [],
        rules: [],
        expected_state: "Extensions Marketplace",
        screen_rules: [
          {
            id: "ui-one",
            kind: "text_present",
            expected: "Extensions Marketplace",
            alternatives: [],
            contradictions: ["Preferences"],
            description: "Open the correct panel.",
          },
        ],
      },
      {
        id: "two",
        title: "Search for the package",
        description: "Enter the package name.",
        dependencies: ["one"],
        timestamp_start: 4,
        timestamp_end: 8,
        reference_frame_id: null,
        object_labels: [],
        rules: [],
        screen_rules: [
          {
            id: "ui-two",
            kind: "text_present",
            expected: "Search results",
            alternatives: [],
            contradictions: [],
            description: "Search first.",
          },
        ],
      },
    ],
  },
};
const provider = {
  mode: "mock" as const,
  configured: true,
  available: true,
  message: "Offline workflow reasoning; actual local OCR.",
};
const check: ScreenCheck = {
  result: {
    step_id: "one",
    status: "uncertain",
    rule_results: [
      {
        rule_id: "ui-one",
        status: "uncertain",
        expected: "Extensions Marketplace",
        observed: "No reliable text",
        evidence: [],
        correction: null,
      },
    ],
    evidence: ["Not enough visible text."],
    explanation: "Increase the text size and show the intended panel.",
    provider_mode: "local_ocr",
    reason: "insufficient_evidence",
    warnings: [],
  },
  observation: {
    elements: [],
    visible_text: "",
    confidence: null,
    image_quality: 0.8,
    provider_mode: "local_ocr",
    complete: false,
    provenance: {},
  },
  completed_step_ids: [],
  current_step_id: "one",
  upcoming_step_id: "two",
  screen_stored: false,
};
const speech = { speak: vi.fn(), cancel: vi.fn() };
function captureDevice() {
  const track = {
    stop: vi.fn(),
    onended: null as (() => void) | null,
    getSettings: () => ({ displaySurface: "browser" }),
  };
  const stream = { getTracks: () => [track], getVideoTracks: () => [track] };
  const getDisplayMedia = vi.fn().mockResolvedValue(stream);
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { getDisplayMedia },
  });
  return { track, stream, getDisplayMedia };
}
function mount(
  props: Partial<React.ComponentProps<typeof LiveScreenAssistant>> = {},
) {
  return render(
    <LiveScreenAssistant
      project={project}
      provider={provider}
      onUpdate={vi.fn()}
      onError={vi.fn()}
      onReview={vi.fn()}
      {...props}
    />,
  );
}
beforeEach(() => {
  vi.spyOn(api, "clearScreenSession").mockResolvedValue(undefined);
  vi.spyOn(api, "screenCheck").mockResolvedValue(check);
  vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
  Object.defineProperty(window, "speechSynthesis", {
    configurable: true,
    value: speech,
  });
  vi.stubGlobal(
    "SpeechSynthesisUtterance",
    class {
      text: string;
      constructor(text: string) {
        this.text = text;
      }
    },
  );
  speech.speak.mockClear();
  speech.cancel.mockClear();
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("digital screen privacy and lifecycle", () => {
  it("does not restore an old Ask response after screen sharing stops", async () => {
    captureDevice();
    let resolve!: (value: {
      answer: string;
      evidence: string[];
      warnings: string[];
      provider_mode: string;
    }) => void;
    const ask = vi.spyOn(api, "ask").mockImplementation(
      () =>
        new Promise((done) => {
          resolve = done;
        }),
    );
    const user = userEvent.setup();
    mount();
    await user.click(
      screen.getByRole("button", { name: "Choose screen or window" }),
    );
    await screen.findByText("SHARING");
    await user.type(
      screen.getByLabelText("Ask about the current workflow"),
      "What next?",
    );
    await user.click(screen.getByRole("button", { name: "Send question" }));
    const signal = ask.mock.calls[0][2];
    await user.click(screen.getByRole("button", { name: "Stop sharing" }));
    expect(signal?.aborted).toBe(true);
    await act(async () => {
      resolve({
        answer: "Stale screen details",
        evidence: ["Previous observation"],
        warnings: [],
        provider_mode: "grounded_template",
      });
      await Promise.resolve();
    });
    expect(screen.queryByText("Stale screen details")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Send question" })).toBeEnabled();
  });
  it("does not request a screen until the user clicks and reports denied selection", async () => {
    const device = captureDevice();
    device.getDisplayMedia.mockRejectedValue(new Error("Denied"));
    const onError = vi.fn();
    const user = userEvent.setup();
    mount({ onError });
    expect(device.getDisplayMedia).not.toHaveBeenCalled();
    await user.click(
      screen.getByRole("button", { name: "Choose screen or window" }),
    );
    await waitFor(() =>
      expect(onError).toHaveBeenCalledWith(
        expect.stringContaining("denied or canceled"),
      ),
    );
    expect(api.screenCheck).not.toHaveBeenCalled();
  });
  it("shows the selected capture scope and stops all tracks plus ephemeral server state", async () => {
    const device = captureDevice();
    const user = userEvent.setup();
    mount();
    await user.click(
      screen.getByRole("button", { name: "Choose screen or window" }),
    );
    expect(
      await screen.findByText("Visible capture scope: browser tab"),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Stop sharing" }));
    expect(device.track.stop).toHaveBeenCalledOnce();
    expect(api.clearScreenSession).toHaveBeenCalledWith(project.id);
    expect(screen.getByText("NOT SHARING")).toBeInTheDocument();
    expect(speech.cancel).toHaveBeenCalled();
  });
  it("immediately cleans up a browser-stopped capture", async () => {
    const device = captureDevice();
    const user = userEvent.setup();
    mount();
    await user.click(
      screen.getByRole("button", { name: "Choose screen or window" }),
    );
    await screen.findByText("SHARING");
    act(() => device.track.onended?.());
    expect(device.track.stop).toHaveBeenCalledOnce();
    expect(screen.getByText("NOT SHARING")).toBeInTheDocument();
  });
  it("stops a late permission response after the component unmounts", async () => {
    const device = captureDevice();
    let resolve!: (stream: unknown) => void;
    device.getDisplayMedia.mockImplementation(
      () =>
        new Promise((done) => {
          resolve = done;
        }),
    );
    const user = userEvent.setup();
    const view = mount();
    await user.click(
      screen.getByRole("button", { name: "Choose screen or window" }),
    );
    view.unmount();
    await act(async () => {
      resolve(device.stream);
      await Promise.resolve();
    });
    expect(device.track.stop).toHaveBeenCalledOnce();
    expect(api.screenCheck).not.toHaveBeenCalled();
  });
  it.each(["meta", "nvidia"] as const)("requires separate per-project %s screen consent before sharing or upload", async (mode) => {
    captureDevice();
    const user = userEvent.setup();
    mount({ provider: { ...provider, mode, configured: false } });
    expect(
      screen.getByRole("button", { name: "Choose screen or window" }),
    ).toBeDisabled();
    expect(
      screen.getByRole("button", { name: "Upload screenshot" }),
    ).toBeDisabled();
    await user.click(screen.getByRole("checkbox", { name: /I consent to sending this project/ }));
    expect(
      screen.getByRole("button", { name: "Choose screen or window" }),
    ).toBeEnabled();
  });
  it("uses local Meta OCR text reasoning without cloud consent or vision-model claims", async () => {
    captureDevice();
    const user = userEvent.setup();
    const onProviderValidated = vi.fn();
    vi.mocked(api.screenCheck).mockResolvedValue({
      ...check, result: { ...check.result, provider_mode: "local_meta" },
      observation: { ...check.observation, provider_mode: "local_meta" },
    });
    mount({ provider: { ...provider, mode: "local_meta", model: "Llama-3.2-3B-Instruct" }, onProviderValidated });
    expect(screen.getByRole("button", { name: "Choose screen or window" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Upload screenshot" })).toBeEnabled();
    expect(screen.queryByRole("checkbox", { name: /I consent to sending/ })).not.toBeInTheDocument();
    expect(screen.queryByText(/No Meta calls in offline mode/)).not.toBeInTheDocument();
    expect(screen.getByText(/Meta Llama receives only redacted OCR text/)).toBeInTheDocument();
    const file = new File(["test screenshot bytes"], "local-screen.png", { type: "image/png" });
    await user.upload(screen.getByLabelText("Upload screen screenshot"), file);
    await screen.findByRole("region", { name: "Screen verification result" });
    expect(screen.getAllByText("LOCAL META LLAMA · OCR + TEXT")).toHaveLength(2);
    expect(api.screenCheck).toHaveBeenCalledWith(project.id, "one", file, false, "",
      "manually selected screenshot", expect.any(AbortSignal), false);
    expect(onProviderValidated).not.toHaveBeenCalled(); // A mode label alone is not validated model provenance.
  });
  it("keeps the final pending checkpoint unfinished until evidence completes it", () => {
    const view = mount({ project: { ...project, completed_step_ids: ["one"] } });
    expect(screen.getByText("Verify this checkpoint to finish")).toBeInTheDocument();
    expect(screen.queryByText("All checkpoints verified", { exact: true })).not.toBeInTheDocument();
    expect(screen.queryByText("All digital checkpoints are verified.")).not.toBeInTheDocument();
    view.rerender(<LiveScreenAssistant project={{ ...project, completed_step_ids: ["one", "two"] }}
      provider={provider} onUpdate={vi.fn()} onError={vi.fn()} onReview={vi.fn()} />);
    expect(screen.getByText("All checkpoints verified", { exact: true })).toBeInTheDocument();
    expect(screen.getByText("All digital checkpoints are verified.")).toBeInTheDocument();
  });
  it("does not carry Meta screen consent into NVIDIA after a provider switch", async () => {
    captureDevice();
    const user = userEvent.setup();
    const props = { project, onUpdate: vi.fn(), onError: vi.fn(), onReview: vi.fn() };
    const view = render(<LiveScreenAssistant {...props} provider={{ ...provider, mode: "meta" }} />);
    await user.click(screen.getByRole("checkbox", { name: /I consent to sending this project/ }));
    expect(screen.getByRole("button", { name: "Upload screenshot" })).toBeEnabled();
    view.rerender(<LiveScreenAssistant {...props} provider={{ ...provider, mode: "nvidia" }} />);
    expect(screen.getByRole("button", { name: "Upload screenshot" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Choose screen or window" })).toBeDisabled();
    expect(screen.getByRole("checkbox", { name: /I consent to sending this project/ })).not.toBeChecked();
    expect(screen.queryByText(/with store:false requested/)).not.toBeInTheDocument();
    expect(api.screenCheck).not.toHaveBeenCalled();
  });
  it("pauses capture and voice, and manual next cannot complete prerequisites", async () => {
    captureDevice();
    const onError = vi.fn();
    const onUpdate = vi.fn();
    const user = userEvent.setup();
    mount({ onError, onUpdate });
    await user.click(
      screen.getByRole("button", { name: "Choose screen or window" }),
    );
    await screen.findByText("SHARING");
    await user.click(screen.getByRole("button", { name: "Pause" }));
    expect(screen.getByText("SHARING · PAUSED")).toBeInTheDocument();
    expect(speech.cancel).toHaveBeenCalled();
    await user.click(
      screen.getByRole("button", { name: "Next eligible step" }),
    );
    expect(onError).toHaveBeenCalledWith(
      expect.stringContaining("Verify the current step"),
    );
    expect(onUpdate).not.toHaveBeenCalled();
  });
  it("uploads actual screenshot bytes, labels OCR honestly, and preserves uncertainty", async () => {
    const user = userEvent.setup();
    const onUpdate = vi.fn();
    mount({ onUpdate });
    const file = new File(["test screenshot bytes"], "screen.png", {
      type: "image/png",
    });
    await user.upload(screen.getByLabelText("Upload screen screenshot"), file);
    expect(
      await screen.findByText(
        "Increase the text size and show the intended panel.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText("LOCAL OCR · REAL SCREEN PIXELS"),
    ).toBeInTheDocument();
    expect(api.screenCheck).toHaveBeenCalledWith(
      project.id,
      "one",
      file,
      false,
      "",
      "manually selected screenshot",
      expect.any(AbortSignal),
      false,
    );
    expect(onUpdate).toHaveBeenCalledWith(
      expect.objectContaining({ completed_step_ids: [] }),
    );
    expect(
      screen.getByText("UNCERTAIN", { selector: ".result-heading .badge" }),
    ).toBeInTheDocument();
  });
  it("ignores a response arriving after stop and aborts its client request", async () => {
    let resolve!: (value: ScreenCheck) => void;
    vi.mocked(api.screenCheck).mockImplementation(
      () =>
        new Promise((done) => {
          resolve = done;
        }),
    );
    const user = userEvent.setup();
    const onUpdate = vi.fn();
    const view = mount({ onUpdate });
    await user.upload(
      screen.getByLabelText("Upload screen screenshot"),
      new File(["pixels"], "screen.png", { type: "image/png" }),
    );
    const signal = vi.mocked(api.screenCheck).mock.calls[0][6];
    view.unmount();
    expect(signal?.aborted).toBe(true);
    await act(async () => {
      resolve(check);
      await Promise.resolve();
    });
    expect(onUpdate).not.toHaveBeenCalled();
  });
  it("keeps evidence retention off until explicitly selected and sends that preference with the capture", async () => {
    const user = userEvent.setup();
    mount();
    const retention = screen.getByRole("checkbox", { name: /Save relevant redacted decision evidence/ });
    expect(retention).not.toBeChecked();
    await user.click(retention);
    await user.upload(screen.getByLabelText("Upload screen screenshot"), new File(["pixels"], "screen.png", { type: "image/png" }));
    await waitFor(() => expect(api.screenCheck).toHaveBeenCalledOnce());
    expect(vi.mocked(api.screenCheck).mock.calls[0][7]).toBe(true);
    expect(screen.getByText(/never screenshots\. Leave this off/)).toBeInTheDocument();
  });
  it("skips duplicate frames, rechecks on a bounded heartbeat, and blocks heartbeat while paused", async () => {
    let now = 1000000;
    vi.spyOn(Date, "now").mockImplementation(() => now);
    let periodic = () => {};
    vi.spyOn(window, "setInterval").mockImplementation((handler, delay) => {
      if (typeof handler === "function" && delay === 4000)
        periodic = handler as () => void;
      return 777 as unknown as ReturnType<typeof window.setInterval>;
    });
    captureDevice();
    const user = userEvent.setup();
    const context = {
      drawImage: vi.fn(),
      fillStyle: "",
      fillRect: vi.fn(),
      getImageData: () => ({ data: new Uint8ClampedArray(160 * 90 * 4) }),
    };
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(
      context as unknown as CanvasRenderingContext2D,
    );
    vi.spyOn(HTMLCanvasElement.prototype, "toBlob").mockImplementation(
      (callback) =>
        callback(new Blob(["actual canvas pixels"], { type: "image/png" })),
    );
    mount();
    await user.click(
      screen.getByRole("button", { name: "Choose screen or window" }),
    );
    await screen.findByText("SHARING");
    const preview = screen.getByLabelText("Shared screen preview");
    Object.defineProperty(preview, "videoWidth", {
      configurable: true,
      value: 1280,
    });
    Object.defineProperty(preview, "videoHeight", {
      configurable: true,
      value: 720,
    });
    fireEvent.loadedData(preview);
    await waitFor(() => expect(api.screenCheck).toHaveBeenCalledOnce());
    await act(async () => {
      periodic();
      await Promise.resolve();
      periodic();
      await Promise.resolve();
    });
    expect(api.screenCheck).toHaveBeenCalledOnce();
    expect(screen.getByText("2 unchanged frames skipped")).toBeInTheDocument();
    now += 20001;
    await act(async () => {
      periodic();
      await Promise.resolve();
    });
    await waitFor(() => expect(api.screenCheck).toHaveBeenCalledTimes(2));
    await user.click(screen.getByRole("button", { name: "Pause" }));
    now += 40000;
    await act(async () => {
      periodic();
      await Promise.resolve();
    });
    expect(api.screenCheck).toHaveBeenCalledTimes(2);
  });
  it("does not repeat voice coaching for confidence-only evidence changes", async () => {
    let now = 1000000;
    vi.spyOn(Date, "now").mockImplementation(() => now);
    captureDevice();
    const context = {
      drawImage: vi.fn(),
      fillStyle: "",
      fillRect: vi.fn(),
      getImageData: () => ({ data: new Uint8ClampedArray(160 * 90 * 4) }),
    };
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(
      context as unknown as CanvasRenderingContext2D,
    );
    vi.spyOn(HTMLCanvasElement.prototype, "toBlob").mockImplementation(
      (callback) =>
        callback(new Blob(["canvas pixels"], { type: "image/png" })),
    );
    const user = userEvent.setup();
    mount();
    await user.click(
      screen.getByRole("button", { name: "Enable voice guidance" }),
    );
    await user.click(
      screen.getByRole("button", { name: "Choose screen or window" }),
    );
    await screen.findByText("SHARING");
    const preview = screen.getByLabelText("Shared screen preview");
    Object.defineProperty(preview, "videoWidth", {
      configurable: true,
      value: 1280,
    });
    Object.defineProperty(preview, "videoHeight", {
      configurable: true,
      value: 720,
    });
    fireEvent.loadedData(preview);
    await waitFor(() => expect(speech.speak).toHaveBeenCalledOnce());
    vi.mocked(api.screenCheck).mockResolvedValue({
      ...check,
      result: {
        ...check.result,
        evidence: ["Character confidence changed from 0.84 to 0.87."],
      },
    });
    now += 11000;
    await user.click(screen.getByRole("button", { name: "Recheck" }));
    await waitFor(() => expect(api.screenCheck).toHaveBeenCalledTimes(2));
    expect(speech.speak).toHaveBeenCalledOnce();
  });
});

describe("digital tutorial ingestion and reproducible sandbox", () => {
  it("requires usage rights and submits a provided transcript without scraping", async () => {
    const save = vi.spyOn(api, "tutorial").mockResolvedValue(project);
    const user = userEvent.setup();
    render(
      <TutorialSource project={project} onUpdate={vi.fn()} onError={vi.fn()} />,
    );
    await user.type(
      screen.getByLabelText("Timestamped transcript"),
      "00:00 Open the Extensions panel.",
    );
    expect(
      screen.getByRole("button", { name: "Save tutorial source" }),
    ).toBeDisabled();
    await user.click(screen.getByRole("checkbox"));
    await user.click(
      screen.getByRole("button", { name: "Save tutorial source" }),
    );
    expect(save).toHaveBeenCalledWith(project.id, {
      transcript: "00:00 Open the Extensions panel.",
      usage_rights_confirmed: true,
    });
  });
  it("shows only user-triggered sandbox checkpoint states and makes no software changes", async () => {
    const user = userEvent.setup();
    render(<CodeLabDemo />);
    expect(screen.getByText(/no actual software changes/)).toBeInTheDocument();
    expect(screen.queryByText("Replay Formatter")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Extensions" }));
    expect(
      screen.getByRole("heading", { name: "Extensions Marketplace" }),
    ).toBeInTheDocument();
    await user.type(
      screen.getByLabelText("Search extensions"),
      "Replay Formatter",
    );
    expect(
      screen.getByRole("heading", { name: "Search results" }),
    ).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: /Replay Formatter.*View details/ }),
    );
    expect(screen.getByText("Extension details")).toBeInTheDocument();
    expect(screen.queryByText("Installed")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Install extension" }));
    expect(screen.getByText("Installed")).toBeInTheDocument();
    expect(screen.getByText("Enabled")).toBeInTheDocument();
  });
  it("introduces visible recoverable wrong-destination, dialog, and version states", async () => {
    const user = userEvent.setup();
    render(<CodeLabDemo />);
    await user.click(screen.getByRole("button", { name: "Settings" }));
    expect(
      screen.getByRole("heading", { name: "Preferences" }),
    ).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Show unexpected dialog" }),
    );
    expect(screen.getByRole("dialog")).toHaveTextContent("Permission denied");
    await user.click(screen.getByRole("button", { name: "Dismiss dialog" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Change UI version" }));
    expect(screen.getAllByText("CodeLab 2.0")).toHaveLength(2);
  });
});
