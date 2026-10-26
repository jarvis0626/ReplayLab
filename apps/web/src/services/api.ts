import type {
  Attempt,
  Evaluation,
  Fixture,
  Graph,
  Health,
  Project,
  Task,
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
  create: (name: string) => post<Project>("/projects", { name }),
  demo: () => post<Project>("/projects/demo", {}),
  remove: (id: string) =>
    request<void>(`/projects/${id}`, { method: "DELETE" }),
  uploadVideo: (id: string, file: File) => {
    const body = new FormData();
    body.append("file", file);
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
  provider: (mode: "mock" | "meta") => post<Health>("/provider", { mode }),
};
