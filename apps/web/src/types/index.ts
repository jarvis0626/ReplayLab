export type Verdict = "pass" | "fail" | "uncertain";
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
}
export interface Task {
  id: string;
  title: string;
  description: string;
  objects: string[];
  steps: Step[];
  provider_mode: string;
  provenance: Record<string, unknown>;
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
  details: {
    id: string;
    title: string;
    expected: Verdict;
    predicted: Verdict;
    correct: boolean;
    explanation: string;
  }[];
  correct: number;
  sample_size: number;
  accuracy: number | null;
  confusion_matrix: Record<string, Record<string, number>>;
  limitations: string[];
}
