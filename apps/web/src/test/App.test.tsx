import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ReactNode } from "react";
import { App } from "../App";
import { Studio } from "../pages/Studio";
import { Practice, VerificationPanel } from "../pages/Practice";
import { TaskWorkspace } from "../pages/TaskWorkspace";
import { EvaluationPage } from "../pages/Evaluation";
import { EvidenceImage, formatTime } from "../components/ui";
import { request } from "../services/api";
import type {
  Attempt,
  Evaluation,
  Graph,
  Project,
  VerificationResult,
} from "../types";

vi.mock("@xyflow/react", async (importOriginal) => {
  const actual = await importOriginal<Record<string, unknown>>();
  return {
    ...actual,
    ReactFlow: ({
      nodes,
      onNodeClick,
      children,
    }: {
      nodes: { id: string; data: { label: ReactNode } }[];
      onNodeClick: (event: unknown, node: { id: string }) => void;
      children: ReactNode;
    }) => (
      <div aria-label="Interactive action graph">
        {nodes.map((node) => (
          <button key={node.id} onClick={() => onNodeClick(null, node)}>
            {node.data.label}
          </button>
        ))}
        {children}
      </div>
    ),
    Background: () => null,
    Controls: () => null,
  };
});

const provider = {
  mode: "mock" as const,
  configured: true,
  available: true,
  message: "Known fixtures only; no live inference.",
};
const project: Project = {
  id: "abc123",
  name: "Block assembly",
  created_at: "2026-10-26T10:00:00Z",
  status: "ready",
  error: null,
  video: {
    url: "/api/media/video.mp4",
    duration: 12,
    width: 640,
    height: 480,
    original_name: "assembly.mp4",
  },
  frames: [{ id: "frame-1", url: "/api/media/frame.png", timestamp: 2 }],
  task: {
    id: "task-1",
    title: "Assemble a tower",
    description: "A controlled tabletop assembly.",
    objects: ["red block", "blue block"],
    provider_mode: "mock",
    provenance: { source: "synthetic fixture" },
    steps: [
      {
        id: "step-1",
        title: "Place the red base",
        description: "Set the red block on the table.",
        dependencies: [],
        timestamp_start: 0,
        timestamp_end: 3,
        reference_frame_id: "frame-1",
        object_labels: ["red block"],
        rules: [
          { id: "r1", kind: "presence", subject: "red block", tolerance: 0.05 },
        ],
      },
      {
        id: "step-2",
        title: "Add the blue block",
        description: "Place blue above red.",
        dependencies: ["step-1"],
        timestamp_start: 3,
        timestamp_end: 6,
        reference_frame_id: "frame-1",
        object_labels: ["red block", "blue block"],
        rules: [
          {
            id: "r2",
            kind: "above",
            subject: "blue block",
            target: "red block",
            tolerance: 0.05,
          },
        ],
      },
    ],
  },
  approved: true,
  completed_step_ids: [],
};
const freshProject: Project = {
  ...project,
  id: "new123",
  name: "My new task",
  status: "new",
  video: null,
  frames: [],
  task: null,
  approved: false,
};
const result: VerificationResult = {
  step_id: "step-1",
  status: "fail",
  observations: [
    { label: "red block", bbox: [0.1, 0.3, 0.4, 0.7], confidence: 0.96 },
  ],
  rule_results: [
    {
      rule_id: "r1",
      kind: "above",
      status: "fail",
      expected: "Blue above red",
      observed: "Blue is right of red",
      correction: "Move blue above the red block.",
      evidence: ["Blue center is to the right."],
    },
  ],
  evidence: ["A visible relative-position mismatch."],
  explanation: "Move the blue block above the red block and capture again.",
  provider_mode: "mock",
};
const attempt: Attempt = {
  id: "attempt-1",
  project_id: project.id,
  step_id: "step-1",
  image_url: "/api/media/attempt.png",
  created_at: "2026-10-26T10:10:00Z",
  result: null,
  status: "ready",
  reference_observations: [],
  error: null,
  task_revision: "revision-1",
};
type Route = unknown | ((init?: RequestInit) => Response | Promise<Response>);
function mockApi(routes: Record<string, Route> = {}) {
  const defaults: Record<string, Route> = {
    "GET /api/health": { status: "ok", provider },
    "GET /api/projects": [],
    "GET /api/demo/fixtures": [],
    [`GET /api/projects/${project.id}/attempts`]: [],
    [`GET /api/projects/${project.id}`]: project,
  };
  const handler = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const key = `${init?.method ?? "GET"} ${String(input)}`;
      const value = { ...defaults, ...routes }[key];
      if (typeof value === "function") return value(init);
      if (value === undefined)
        return Response.json(
          { detail: `No test route: ${key}` },
          { status: 404 },
        );
      return Response.json(value);
    },
  );
  vi.stubGlobal("fetch", handler);
  return handler;
}
afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("workspace navigation and project lifecycle", () => {
  it("loads actual project counts and clearly labels offline mode", async () => {
    mockApi({ "GET /api/projects": [project] });
    render(<App />);
    expect(await screen.findByText("MOCK MODE")).toBeInTheDocument();
    expect(screen.getByText("Teach once.")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Block assembly.*Ready/ }),
    ).toBeInTheDocument();
    expect(screen.getByText("Verified steps")).toBeInTheDocument();
  });
  it("creates a named project and opens the video studio", async () => {
    const fetcher = mockApi({ "POST /api/projects": freshProject });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("MOCK MODE");
    await user.click(screen.getAllByRole("button", { name: "New project" })[1]);
    await user.type(screen.getByLabelText("Project name"), "My new task");
    await user.click(
      within(screen.getByRole("dialog")).getByRole("button", {
        name: /Create project/,
      }),
    );
    expect(await screen.findByText("Demonstration studio")).toBeInTheDocument();
    const call = fetcher.mock.calls.find(
      ([path, init]) => path === "/api/projects" && init?.method === "POST",
    );
    expect(JSON.parse(String(call?.[1]?.body))).toEqual({
      name: "My new task",
    });
  });
  it("shows a real API failure without pretending a project was created", async () => {
    mockApi({
      "POST /api/projects": () =>
        Response.json(
          { detail: "Project store is unavailable." },
          { status: 503 },
        ),
    });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("MOCK MODE");
    await user.click(screen.getAllByRole("button", { name: "New project" })[1]);
    await user.type(screen.getByLabelText("Project name"), "My task");
    await user.click(
      within(screen.getByRole("dialog")).getByRole("button", {
        name: /Create project/,
      }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Project store is unavailable.",
    );
    expect(screen.queryByText("Demonstration studio")).not.toBeInTheDocument();
  });
  it("switches provider visibly without initiating cloud inference", async () => {
    const fetcher = mockApi({
      "POST /api/provider": {
        provider: {
          ...provider,
          mode: "meta",
          available: false,
          configured: false,
          message: "Meta API key is missing.",
        },
      },
    });
    const user = userEvent.setup();
    render(<App />);
    await screen.findByText("MOCK MODE");
    await user.click(
      screen.getByRole("button", { name: "Open provider settings" }),
    );
    await user.click(
      screen.getByRole("button", { name: /Meta Model API.*Muse Spark/ }),
    );
    expect(await screen.findByText("META MODE")).toBeInTheDocument();
    expect(screen.getByText("Meta API key is missing.")).toBeInTheDocument();
    expect(
      fetcher.mock.calls.filter(([path]) => String(path).includes("extract")),
    ).toHaveLength(0);
  });
});

describe("video studio", () => {
  it("rejects unsupported media before posting an upload", async () => {
    const fetcher = mockApi();
    const user = userEvent.setup({ applyAccept: false });
    render(
      <Studio
        project={freshProject}
        provider={provider}
        consent={false}
        onUpdate={vi.fn()}
        onTask={vi.fn()}
        onError={vi.fn()}
      />,
    );
    await user.upload(
      screen.getByLabelText("Upload demonstration video"),
      new File(["no video"], "notes.txt", { type: "text/plain" }),
    );
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Choose an MP4, MOV, WebM, or AVI video.",
    );
    expect(fetcher).not.toHaveBeenCalled();
  });
  it("posts a real file and keeps asynchronous processing visible", async () => {
    const pending = { ...freshProject, status: "processing" as const };
    const onUpdate = vi.fn();
    const fetcher = mockApi({ "POST /api/projects/new123/video": pending });
    const user = userEvent.setup();
    const { rerender } = render(
      <Studio
        project={freshProject}
        provider={provider}
        consent={false}
        onUpdate={onUpdate}
        onTask={vi.fn()}
        onError={vi.fn()}
      />,
    );
    await user.upload(
      screen.getByLabelText("Upload demonstration video"),
      new File(["test video bytes"], "demo.mp4", { type: "video/mp4" }),
    );
    await waitFor(() => expect(onUpdate).toHaveBeenCalledWith(pending));
    expect(fetcher.mock.calls[0][1]?.body).toBeInstanceOf(FormData);
    rerender(
      <Studio
        project={pending}
        provider={provider}
        consent={false}
        onUpdate={onUpdate}
        onTask={vi.fn()}
        onError={vi.fn()}
      />,
    );
    expect(
      screen.getByText("Processing your demonstration…"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /Extracting task/ }),
    ).toBeDisabled();
  });
  it("keeps live extraction disabled until cloud consent is explicit", () => {
    render(
      <Studio
        project={project}
        provider={{ ...provider, mode: "meta" }}
        consent={false}
        onUpdate={vi.fn()}
        onTask={vi.fn()}
        onError={vi.fn()}
      />,
    );
    expect(
      screen.getByRole("button", { name: /Generate task steps/ }),
    ).toBeDisabled();
    expect(
      screen.getByText(/Enable cloud-processing consent/),
    ).toBeInTheDocument();
  });
});

describe("task review and dependency graph", () => {
  const graph: Graph = {
    nodes: project.task!.steps.map((s, i) => ({
      ...s,
      status: i === 0 ? "current" : "pending",
    })),
    edges: [{ source: "step-1", target: "step-2" }],
    order: ["step-1", "step-2"],
  };
  it("renders graph actions and requires explicit approval", async () => {
    const onUpdate = vi.fn();
    mockApi({
      "GET /api/projects/abc123/graph": graph,
      "POST /api/projects/abc123/approve": project,
    });
    const user = userEvent.setup();
    render(
      <TaskWorkspace
        project={{ ...project, approved: false }}
        onUpdate={onUpdate}
        onError={vi.fn()}
        onPractice={vi.fn()}
      />,
    );
    expect(
      await screen.findByRole("button", { name: /STEP 1.*Place the red base/ }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: "Frame 1 · 0:02.0" }),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Approve task" }));
    await waitFor(() => expect(onUpdate).toHaveBeenCalledWith(project));
  });
  it("persists edits through task validation and surfaces rejected dependencies", async () => {
    const onError = vi.fn();
    const fetcher = mockApi({
      "GET /api/projects/abc123/graph": graph,
      "PUT /api/projects/abc123/task": () =>
        Response.json(
          { detail: "The task graph contains a dependency cycle." },
          { status: 422 },
        ),
    });
    const user = userEvent.setup();
    render(
      <TaskWorkspace
        project={project}
        onUpdate={vi.fn()}
        onError={onError}
        onPractice={vi.fn()}
      />,
    );
    await user.clear(screen.getByLabelText("Step title"));
    await user.type(screen.getByLabelText("Step title"), "Revised base step");
    await user.click(screen.getByRole("button", { name: /Save changes/ }));
    await waitFor(() =>
      expect(onError).toHaveBeenCalledWith(
        "The task graph contains a dependency cycle.",
      ),
    );
    const call = fetcher.mock.calls.find(([, init]) => init?.method === "PUT");
    expect(JSON.parse(String(call?.[1]?.body)).steps[0].title).toBe(
      "Revised base step",
    );
  });
  it("allows typing multiple object labels without erasing comma separators", async () => {
    const fetcher = mockApi({
      "GET /api/projects/abc123/graph": graph,
      "PUT /api/projects/abc123/task": project,
    });
    const user = userEvent.setup();
    render(
      <TaskWorkspace
        project={project}
        onUpdate={vi.fn()}
        onError={vi.fn()}
        onPractice={vi.fn()}
      />,
    );
    const field = screen.getByLabelText("Objects (comma separated)");
    await user.clear(field);
    await user.type(field, "red block, blue block");
    expect(field).toHaveValue("red block, blue block");
    await user.click(screen.getByRole("button", { name: /Save changes/ }));
    const call = fetcher.mock.calls.find(([, init]) => init?.method === "PUT");
    expect(JSON.parse(String(call?.[1]?.body)).steps[0].object_labels).toEqual([
      "red block",
      "blue block",
    ]);
  });
});

describe("guided practice and evidence", () => {
  it("blocks verification before the user approves instructions", () => {
    mockApi();
    render(
      <Practice
        project={{ ...project, approved: false }}
        provider={provider}
        consent={false}
        onUpdate={vi.fn()}
        onError={vi.fn()}
        onReview={vi.fn()}
      />,
    );
    expect(
      screen.getByText("Review first. Then learn by doing."),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Verify checkpoint/ }),
    ).not.toBeInTheDocument();
  });
  it("uploads a checkpoint, submits evidence attestations, and displays a grounded correction", async () => {
    const onUpdate = vi.fn();
    const fetcher = mockApi({
      "POST /api/projects/abc123/attempts": attempt,
      "POST /api/attempts/attempt-1/verify": {
        ...attempt,
        result,
        status: "verified",
      },
    });
    const user = userEvent.setup();
    render(
      <Practice
        project={project}
        provider={provider}
        consent={false}
        onUpdate={onUpdate}
        onError={vi.fn()}
        onReview={vi.fn()}
      />,
    );
    expect(
      screen.getByRole("button", {
        name: /Add the blue block.*Complete prerequisites/,
      }),
    ).toBeDisabled();
    await user.upload(
      screen.getByLabelText("Upload checkpoint image"),
      new File(["image bytes"], "checkpoint.png", { type: "image/png" }),
    );
    await screen.findByRole("button", { name: "Verify checkpoint" });
    await user.click(
      screen.getByLabelText(
        "Reference and checkpoint use a comparable camera view",
      ),
    );
    await user.click(
      screen.getByLabelText("All required objects are visible in both images"),
    );
    await user.click(screen.getByRole("button", { name: "Verify checkpoint" }));
    expect(
      await screen.findByText("One checkpoint needs a correction."),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Move blue above the red block."),
    ).toBeInTheDocument();
    expect(screen.getByText("Blue is right of red")).toBeInTheDocument();
    const call = fetcher.mock.calls.find(
      ([path]) => path === "/api/attempts/attempt-1/verify",
    );
    expect(JSON.parse(String(call?.[1]?.body))).toEqual({
      cloud_consent: false,
      comparable: true,
      visibility_confirmed: true,
    });
    await waitFor(() => expect(onUpdate).toHaveBeenCalledWith(project));
  });
  it("handles camera denial and retains the manual upload path", async () => {
    mockApi();
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: vi.fn().mockRejectedValue(new Error("Permission denied")),
      },
    });
    const user = userEvent.setup();
    render(
      <Practice
        project={project}
        provider={provider}
        consent={false}
        onUpdate={vi.fn()}
        onError={vi.fn()}
        onReview={vi.fn()}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Start camera" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Camera access was denied",
    );
    expect(screen.getByRole("button", { name: "Upload image" })).toBeEnabled();
  });
  it("stops every camera track when a checkpoint replaces the live preview", async () => {
    mockApi({ "POST /api/projects/abc123/attempts": attempt });
    const stop = vi.fn();
    Object.defineProperty(navigator, "mediaDevices", {
      configurable: true,
      value: {
        getUserMedia: vi
          .fn()
          .mockResolvedValue({ getTracks: () => [{ stop }] }),
      },
    });
    vi.spyOn(HTMLMediaElement.prototype, "play").mockResolvedValue();
    const user = userEvent.setup();
    render(
      <Practice
        project={project}
        provider={provider}
        consent={false}
        onUpdate={vi.fn()}
        onError={vi.fn()}
        onReview={vi.fn()}
      />,
    );
    await user.click(screen.getByRole("button", { name: "Start camera" }));
    await screen.findByLabelText("Live camera preview");
    await user.upload(
      screen.getByLabelText("Upload checkpoint image"),
      new File(["image"], "checkpoint.png", { type: "image/png" }),
    );
    await screen.findByAltText("Your checkpoint attempt");
    expect(stop).toHaveBeenCalledOnce();
    expect(
      screen.queryByLabelText("Live camera preview"),
    ).not.toBeInTheDocument();
  });
  it("does not promote uncertain evidence into a pass", () => {
    render(
      <VerificationPanel
        result={{
          ...result,
          status: "uncertain",
          observations: [],
          rule_results: [],
          explanation: "The required component is occluded.",
        }}
        onRetry={vi.fn()}
      />,
    );
    expect(screen.getByText("UNCERTAIN")).toBeInTheDocument();
    expect(
      screen.getByText("The required component is occluded."),
    ).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /Next checkpoint/ }),
    ).not.toBeInTheDocument();
  });
  it("places normalized object boxes on their actual evidence image", () => {
    const { container } = render(
      <EvidenceImage
        src="/checkpoint.png"
        alt="Checkpoint"
        observations={result.observations}
      />,
    );
    const overlay = container.querySelector(".observation-box");
    expect(overlay).toHaveStyle({
      left: "10%",
      top: "30%",
      width: "30.000000000000004%",
      height: "40%",
    });
    expect(screen.getByText("red block · 96%")).toBeInTheDocument();
  });
});

describe("measured evaluation and API failures", () => {
  it("keeps source timestamp precision to a tenth of a second and handles minute rollover", () => {
    expect(formatTime(2.56)).toBe("0:02.6");
    expect(formatTime(59.97)).toBe("1:00.0");
    expect(formatTime(62.04)).toBe("1:02.0");
  });
  it("renders measured sample size, predictions, and explicit limitations", async () => {
    const evaluation: Evaluation = {
      sample_size: 1,
      correct: 1,
      accuracy: 1,
      details: [
        {
          id: "case-1",
          title: "Occluded component",
          expected: "uncertain",
          predicted: "uncertain",
          correct: true,
          explanation: "Visibility annotation is insufficient.",
        },
      ],
      confusion_matrix: {
        pass: { pass: 0, fail: 0, uncertain: 0 },
        fail: { pass: 0, fail: 0, uncertain: 0 },
        uncertain: { pass: 0, fail: 0, uncertain: 1 },
      },
      limitations: ["Curated observations do not measure live model accuracy."],
    };
    mockApi({ "GET /api/projects/abc123/evaluation": evaluation });
    const user = userEvent.setup();
    render(<EvaluationPage project={project} onError={vi.fn()} />);
    expect(
      await screen.findByText("100.0% agreement · curated fixtures"),
    ).toBeInTheDocument();
    expect(screen.getByText("1 cases")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Curated observations do not measure live model accuracy.",
      ),
    ).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", { name: "Occluded component" }),
    );
    expect(
      screen.getByText("Visibility annotation is insufficient."),
    ).toBeInTheDocument();
  });
  it("preserves server validation details and gives a useful offline error", async () => {
    mockApi({
      "GET /api/test": () =>
        Response.json(
          { detail: [{ msg: "Invalid reference frame." }] },
          { status: 422 },
        ),
    });
    await expect(request("/test")).rejects.toThrow("Invalid reference frame.");
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new Error("Network error")),
    );
    await expect(request("/health")).rejects.toThrow("Cannot reach ReplayLab.");
  });
});
