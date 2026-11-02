import type {
  Attempt,
  Evaluation,
  Fixture,
  Graph,
  Health,
  Project,
  Modality,
  ScreenCheck,
  Task,
  WorkflowVerification,
  Verdict,
  ProviderMode,
} from "../types";

export async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  let response: Response;
  try {
    response = await fetch(`/api${path}`, { ...init, headers });
  } catch {
    if (init.signal?.aborted)
      throw new DOMException("Request canceled", "AbortError");
    throw new Error(
      "Cannot reach ReplayLab. Check that the API is running on port 8010.",
    );
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail: unknown = body.detail ?? body.message;
    const message =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail.map((item) => item.msg ?? "Invalid input").join("; ")
          : `Request failed (${response.status}).`;
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
const post = <T>(path: string, data: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(data) });
export const api = {
  health: () => request<Health>("/health"),
  projects: () => request<Project[]>("/projects"),
  project: (id: string) => request<Project>(`/projects/${id}`),
  create: (name: string, modality: Modality = "physical") =>
    post<Project>(
      "/projects",
      modality === "physical" ? { name } : { name, modality },
    ),
  demo: () => post<Project>("/projects/demo", {}),
  digitalDemo: () => post<Project>("/projects/digital-demo", {}),
  tutorial: (
    id: string,
    data: {
      youtube_url?: string;
      transcript?: string;
      title?: string;
      usage_rights_confirmed: boolean;
    },
  ) => post<Project>(`/projects/${id}/tutorial`, data),
  screenCheck: (
    id: string,
    stepId: string,
    file: Blob,
    consent: boolean,
    interfaceVersion: string,
    sourceScope: string,
    signal?: AbortSignal,
    retainEvidence = false,
  ) => {
    const body = new FormData();
    body.append("file", file, "screen-check.png");
    body.append("step_id", stepId);
    body.append("cloud_consent", String(consent));
    if (interfaceVersion) body.append("interface_version", interfaceVersion);
    body.append("source_scope", sourceScope);
    body.append("retain_evidence", String(retainEvidence));
    return request<ScreenCheck>(`/projects/${id}/screen-check`, {
      method: "POST",
      body,
      signal,
    });
  },
  clearScreenSession: (id: string) =>
    post<void>(`/projects/${id}/screen-session/clear`, {}),
  ask: (id: string, question: string, signal?: AbortSignal) =>
    request<{
      answer: string;
      evidence: string[];
      warnings: string[];
      provider_mode: string;
    }>(`/projects/${id}/ask`, {
      method: "POST",
      body: JSON.stringify({ question }),
      signal,
    }),
  remove: (id: string) =>
    request<void>(`/projects/${id}`, { method: "DELETE" }),
  uploadVideo: (id: string, file: File, usageRightsConfirmed = false) => {
    const body = new FormData();
    body.append("file", file);
    body.append("usage_rights_confirmed", String(usageRightsConfirmed));
    return request<Project>(`/projects/${id}/video`, { method: "POST", body });
  },
  extract: (id: string, cloud_consent: boolean) =>
    post<Project>(`/projects/${id}/extract`, { cloud_consent }),
  saveTask: (id: string, task: Task) =>
    request<Project>(`/projects/${id}/task`, {
      method: "PUT",
      body: JSON.stringify(task),
    }),
  approve: (id: string) =>
    post<Project>(`/projects/${id}/approve`, { approved: true }),
  graph: (id: string) => request<Graph>(`/projects/${id}/graph`),
  attempts: (id: string) => request<Attempt[]>(`/projects/${id}/attempts`),
  uploadAttempt: (id: string, stepId: string, file: File) => {
    const body = new FormData();
    body.append("file", file);
    body.append("step_id", stepId);
    return request<Attempt>(`/projects/${id}/attempts`, {
      method: "POST",
      body,
    });
  },
  verify: (
    id: string,
    cloud_consent: boolean,
    comparable: boolean | null,
    visibility_confirmed: boolean,
  ) =>
    post<Attempt>(`/attempts/${id}/verify`, {
      cloud_consent,
      comparable,
      visibility_confirmed,
    }),
  fixtures: () => request<Fixture[]>("/demo/fixtures"),
  evaluation: (id: string) => request<Evaluation>(`/projects/${id}/evaluation`),
  digitalEvaluation: () => request<Evaluation>("/evaluation/digital"),
  runDigitalEvaluation: () => post<Evaluation>("/evaluation/digital/run", {}),
  nvidiaEvaluation: () => request<Evaluation>("/evaluation/nvidia"),
  runNvidiaEvaluation: (cloud_consent: boolean) => post<Evaluation>("/evaluation/nvidia/run", { cloud_consent }),
  verifications: (id: string) => request<WorkflowVerification[]>(`/projects/${id}/verifications`),
  reportVerification: (id: string, verificationId: string, expected_verdict: Verdict, notes: string) =>
    post<{ id: string }>(`/projects/${id}/verifications/${verificationId}/feedback`, { expected_verdict, notes }),
  provider: (mode: ProviderMode) => post<Health>("/provider", { mode }),
};
