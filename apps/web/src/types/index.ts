export type Verdict = "pass" | "fail" | "uncertain";
export type Modality = "physical" | "digital";
export interface ScreenRule {
  id: string;
  kind:
    | "text_present"
    | "text_absent"
    | "window"
    | "path"
    | "selection"
    | "error_absent";
  expected: string;
  alternatives: string[];
  contradictions: string[];
  description: string;
}
export interface Tutorial {
  kind: "youtube" | "transcript" | "demo";
  youtube_id?: string | null;
  title: string;
  transcript_segments: { start: number; end: number; text: string }[];
  embed_url?: string | null;
  requires_rights_review?: boolean;
  usage_rights_confirmed?: boolean;
  instruction_warnings?: string[];
}
export interface Provider {
  mode: "mock" | "meta";
  configured: boolean;
  available: boolean;
  message: string;
}
export interface Health {
  status: string;
  provider: Provider;
}
export interface Frame {
  id: string;
  url: string;
  timestamp: number;
}
export interface Rule {
  id: string;
  kind:
    | "presence"
    | "count"
    | "above"
    | "below"
    | "left"
    | "right"
    | "near"
    | "aligned"
    | "color";
  subject: string;
  target?: string | null;
  value?: number | string | boolean | null;
  tolerance: number;
}
export interface Step {
  id: string;
  title: string;
  description: string;
  dependencies: string[];
  timestamp_start: number;
  timestamp_end: number;
  reference_frame_id: string | null;
  object_labels: string[];
  rules: Rule[];
  expected_state?: string;
  screen_rules?: ScreenRule[];
}
export interface Task {
  interface_version?: string | null;
  id: string;
  title: string;
  description: string;
  objects: string[];
  steps: Step[];
  provider_mode: string;
  provenance: Record<string, unknown>;
  modality?: Modality;
}
export interface Project {
  id: string;
  name: string;
  created_at: string;
  status: "new" | "processing" | "ready" | "error";
  error: string | null;
  video: {
    url: string;
    duration: number;
    width: number;
    height: number;
    original_name: string;
  } | null;
  frames: Frame[];
  task: Task | null;
  approved: boolean;
  completed_step_ids: string[];
  modality?: Modality;
  tutorial?: Tutorial | null;
}
export interface ScreenObservation {
  elements: {
    text: string;
    role: string;
    bbox?: [number, number, number, number] | null;
    confidence: number | null;
    source: string;
  }[];
  visible_text: string;
  confidence: number | null;
  image_quality: number | null;
  provider_mode: string;
  interface_version?: string | null;
  complete: boolean;
  provenance: Record<string, unknown>;
}
export interface ScreenResult {
  step_id: string;
  status: Verdict;
  rule_results: {
    rule_id: string;
    status: Verdict;
    expected: string;
    observed: string;
    evidence: string[];
    correction: string | null;
  }[];
  evidence: string[];
  explanation: string;
  provider_mode: string;
  reason?: string | null;
  observed_step_id?: string | null;
  warnings: string[];
}
export interface ScreenCheck {
  verification?: WorkflowVerification | null;
  result: ScreenResult;
  observation: ScreenObservation;
  completed_step_ids: string[];
  current_step_id?: string | null;
  upcoming_step_id?: string | null;
  screen_stored: boolean;
  source_scope?: string;
}
export interface Observation {
  label: string;
  bbox: [number, number, number, number];
  confidence: number | null;
  [key: string]: unknown;
}
export interface VerificationResult {
  step_id: string;
  status: Verdict;
  observations: Observation[];
  rule_results: {
    rule_id: string;
    kind: Rule["kind"];
    status: Verdict;
    evidence: string[];
    expected: string;
    observed: string;
    correction: string | null;
  }[];
  evidence: string[];
  explanation: string;
  provider_mode: string;
}
export interface Attempt {
  verification?: WorkflowVerification | null;
  id: string;
  project_id: string;
  step_id: string;
  image_url: string;
  created_at: string;
  result: VerificationResult | null;
  status: string;
  reference_observations: Observation[];
  error: string | null;
  task_revision: string;
}
export interface Fixture {
  id: string;
  label: string;
  url: string;
  description: string;
}
export interface Graph {
  nodes: (Step & { status: "completed" | "current" | "pending" })[];
  edges: { source: string; target: string }[];
  order: string[];
}
export interface Evaluation {
  dataset?: string;
  provider_mode?: string;
  evaluation_kind?: string;
  measured_at?: string;
  target_size?: number;
  decisive_accuracy?: number | null;
  decisive_predictions?: number;
  false_certainty_rate?: number | null;
  false_certainty_count?: number;
  uncertain_ground_truth_count?: number;
  uncertainty_recall?: number | null;
  decisive_misclassifications?: number;
  latency_ms?: { sample_size: number; median: number | null; p95: number | null; min: number | null; max: number | null };
  details: {
    id: string;
    title: string;
    expected: Verdict;
    predicted: Verdict;
    correct: boolean;
    explanation: string;
    category?: string;
    evidence?: string[];
    processing_latency_ms?: number;
    screenshot_url?: string;
    reference_step_id?: string;
    expected_conditions?: string[];
    observed_conditions?: string[];
    failure_notes?: string[];
  }[];
  correct: number;
  sample_size: number;
  accuracy: number | null;
  confusion_matrix: Record<string, Record<string, number>>;
  limitations: string[];
}

export interface WorkflowVerification {
  id: string;
  workflow_id: string;
  task_id: string;
  step_id: string;
  modality: Modality;
  verdict: Verdict;
  expected_conditions: string[];
  observed_conditions: string[];
  constraints: { id: string; kind: string; verdict: Verdict; expected: string; observed: string; evidence: string[]; correction: string | null }[];
  evidence_references: { id: string; kind: string; text: string; source: string; timestamp?: number | null }[];
  uncertainty_reasons: string[];
  correction: string | null;
  explanation: string;
  provider: { mode: string; observation: string; explanation: string };
  mismatch_classification: string | null;
  latency_ms: number;
  created_at: string;
  task_revision: string;
  retained: boolean;
}
