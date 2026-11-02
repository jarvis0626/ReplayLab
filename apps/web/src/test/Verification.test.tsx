import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { EvidenceInspector, VerificationHistory } from "../components/EvidenceInspector";
import { EvaluationPage } from "../pages/Evaluation";
import { api } from "../services/api";
import type { Evaluation, Project, WorkflowVerification } from "../types";

const decision: WorkflowVerification = {
  id: "decision-1", workflow_id: "workflow-1", task_id: "task-1", step_id: "step-1", modality: "digital", verdict: "uncertain",
  expected_conditions: ["Extensions panel visible"], observed_conditions: ["CodeLab 2.0 visible"], constraints: [],
  evidence_references: [{ id: "ref-1", kind: "visible_observation", text: "CodeLab 2.0", source: "local_ocr" }],
  uncertainty_reasons: ["The visible version differs from the approved reference."], correction: "Show the matching version.",
  explanation: "The screen differs.", provider: { mode: "mock", observation: "local_ocr", explanation: "deterministic_template" },
  mismatch_classification: "confirmed_version_mismatch", latency_ms: 45, created_at: "2026-10-28T10:00:00Z", task_revision: "revision-1", retained: false,
};
const report: Evaluation = {
  dataset: "Captured CodeLab attempts", provider_mode: "local_ocr", evaluation_kind: "controlled_browser_pixels", sample_size: 2, target_size: 20, correct: 1, accuracy: .5,
  decisive_accuracy: 0, decisive_predictions: 1, false_certainty_rate: .5, false_certainty_count: 1, uncertain_ground_truth_count: 2,
  uncertainty_recall: .5, decisive_misclassifications: 0, latency_ms: { sample_size: 2, median: 200, p95: 295, min: 100, max: 300 },
  confusion_matrix: { pass: { pass: 0, fail: 0, uncertain: 0 }, fail: { pass: 0, fail: 0, uncertain: 0 }, uncertain: { pass: 1, fail: 0, uncertain: 1 } },
  details: [{ id: "case-1", title: "Version changed", expected: "uncertain", predicted: "pass", correct: false, explanation: "Missing version evidence.", processing_latency_ms: 100, screenshot_url: "/api/evaluation/digital/assets/case-1.png", evidence: ["A visible header"], failure_notes: ["False certainty is retained in the report."] }, { id: "case-2", title: "Obscured panel", expected: "uncertain", predicted: "uncertain", correct: true, explanation: "Panel is not visible.", processing_latency_ms: 300 }],
  limitations: ["Controlled authored labels; live Meta was not evaluated."],
};
afterEach(() => { vi.restoreAllMocks(); });

describe("inspectable shared verification evidence", () => {
  it("shows the measured latency, version evidence and abstention reason without changing a verdict", async () => {
    const user = userEvent.setup();
    render(<EvidenceInspector verification={decision} />);
    expect(screen.getByText("45 ms")).toBeInTheDocument();
    expect(screen.getByText("confirmed version mismatch")).toBeInTheDocument();
    expect(screen.getByText("The visible version differs from the approved reference.")).toBeInTheDocument();
    await user.click(screen.getByText("Inspect decision and source evidence"));
    expect(screen.getByText("CodeLab 2.0")).toBeInTheDocument();
    expect(screen.getByText(/temporary unless you explicitly choose/)).toBeInTheDocument();
  });
  it("requires a submitted feedback form and preserves the deterministic result", async () => {
    const save = vi.spyOn(api, "reportVerification").mockResolvedValue({ id: "feedback-1" });
    const user = userEvent.setup();
    render(<EvidenceInspector verification={decision} />);
    expect(save).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Report incorrect evaluation" }));
    await user.selectOptions(screen.getByLabelText("Expected verdict for this evaluation"), "fail");
    await user.type(screen.getByLabelText("Evaluation report notes"), "The wrong destination is visible.");
    await user.click(screen.getByRole("button", { name: "Save evaluation report" }));
    await waitFor(() => expect(save).toHaveBeenCalledWith("workflow-1", "decision-1", "fail", "The wrong destination is visible."));
    expect(await screen.findByRole("status")).toHaveTextContent("does not change the verdict");
    expect(decision.verdict).toBe("uncertain");
  });
  it("loads only saved evidence on request and opens the selected decision", async () => {
    const load = vi.spyOn(api, "verifications").mockResolvedValue([{ ...decision, retained: true }]);
    const user = userEvent.setup();
    render(<VerificationHistory projectId="workflow-1" onError={vi.fn()} />);
    expect(load).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Load saved evidence" }));
    await user.click(await screen.findByRole("button", { name: /step-1/ }));
    expect(screen.getByText("SAVED EVIDENCE")).toBeInTheDocument();
    expect(screen.getByText(/digital screenshots are never saved/)).toBeInTheDocument();
  });
});

describe("digital evaluation calibration", () => {
  it("keeps NVIDIA evaluation unknown and requires separate consent before spending API credits", async () => {
    vi.spyOn(api, "digitalEvaluation").mockResolvedValue(report);
    const load = vi.spyOn(api, "nvidiaEvaluation").mockResolvedValue({
      ...report, provider_mode: "nvidia", sample_size: 0, correct: 0, accuracy: null,
      details: [], decisive_accuracy: null, false_certainty_rate: null, uncertainty_recall: null,
      model: "meta/configured-test-model", host: "integrate.api.nvidia.com",
      skipped: [{ id: "case-auth", reason: "NVIDIA authentication failed; no prediction." }],
    });
    const run = vi.spyOn(api, "runNvidiaEvaluation").mockResolvedValue({ ...report, provider_mode: "nvidia" });
    const user = userEvent.setup();
    render(<EvaluationPage project={{ id: "workflow-1", modality: "digital" } as Project} onError={vi.fn()} />);
    await screen.findByText("2 cases");
    await user.click(screen.getByRole("button", { name: "NVIDIA model evaluation" }));
    expect(await screen.findByText("0 cases")).toBeInTheDocument();
    expect(load).toHaveBeenCalledOnce();
    expect(screen.getByText(/No completed live model cases/)).toBeInTheDocument();
    expect(screen.getByText(/NVIDIA authentication failed; no prediction/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run evaluation" })).toBeDisabled();
    expect(run).not.toHaveBeenCalled();
    await user.click(screen.getByRole("checkbox", { name: /I consent to sending up to 20/ }));
    await user.click(screen.getByRole("button", { name: "Run evaluation" }));
    await waitFor(() => expect(run).toHaveBeenCalledWith(true));
  });
  it("shows actual incomplete count, false certainty, latency and visible failures without inventing results", async () => {
    vi.spyOn(api, "digitalEvaluation").mockResolvedValue(report);
    const run = vi.spyOn(api, "runDigitalEvaluation").mockResolvedValue(report);
    const user = userEvent.setup();
    render(<EvaluationPage project={{ id: "workflow-1", modality: "digital" } as Project} onError={vi.fn()} />);
    expect(await screen.findByText("2 cases")).toBeInTheDocument();
    expect(screen.getByText(/2 completed \/ 20 target cases/)).toBeInTheDocument();
    expect(screen.getByText(/not an independent human study/)).toBeInTheDocument();
    expect(screen.getByText("200 ms")).toBeInTheDocument();
    expect(screen.getByText("Mismatch")).toBeInTheDocument();
    const calibration = screen.getByText("False certainty").closest("div")!;
    expect(within(calibration).getByText("50.0%")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Version changed" }));
    expect(screen.getByAltText("Actual evaluation capture: Version changed")).toHaveAttribute("src", "/api/evaluation/digital/assets/case-1.png");
    expect(screen.getByText("False certainty is retained in the report.")).toBeInTheDocument();
    expect(run).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Run evaluation" }));
    await waitFor(() => expect(run).toHaveBeenCalledOnce());
  });
});
