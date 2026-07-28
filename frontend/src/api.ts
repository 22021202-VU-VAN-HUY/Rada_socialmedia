import type {
  AuthResult,
  BrowserAgent,
  BrowserAgentPairingCode,
  Connection,
  ConnectionResult,
  ContentPage,
  Job,
  Overview,
  RunConfiguration,
  Source,
  User,
} from "./types";

const TOKEN_KEY = "talent-radar-token";
const USER_KEY = "talent-radar-user";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

export function readSession(): { token: string; user: User } | null {
  const token = localStorage.getItem(TOKEN_KEY);
  const rawUser = localStorage.getItem(USER_KEY);
  if (!token || !rawUser) return null;
  try {
    return { token, user: JSON.parse(rawUser) as User };
  } catch {
    clearSession();
    return null;
  }
}

export function storeSession(result: AuthResult): void {
  localStorage.setItem(TOKEN_KEY, result.access_token);
  localStorage.setItem(USER_KEY, JSON.stringify(result.user));
}

export function clearSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

async function request<T>(
  path: string,
  options: RequestInit = {},
  authenticated = true,
): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body) headers.set("Content-Type", "application/json");
  const token = localStorage.getItem(TOKEN_KEY);
  if (authenticated && token) headers.set("Authorization", `Bearer ${token}`);
  let response: Response;
  try {
    response = await fetch(path, { ...options, headers });
  } catch {
    throw new ApiError("Không kết nối được với Talent Radar.", 0);
  }
  if (response.status === 401 && authenticated) {
    clearSession();
    window.dispatchEvent(new Event("talent-radar:session-expired"));
  }
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const payload = (await response.json()) as { detail?: string };
      detail = payload.detail || detail;
    } catch {
      // Keep the HTTP status text.
    }
    throw new ApiError(detail, response.status);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function queryString(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") search.set(key, String(value));
  }
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}

export const api = {
  login: (email: string, password: string) =>
    request<AuthResult>(
      "/auth/login",
      { method: "POST", body: JSON.stringify({ email, password }) },
      false,
    ),
  register: (email: string, password: string) =>
    request<AuthResult>(
      "/auth/register",
      { method: "POST", body: JSON.stringify({ email, password }) },
      false,
    ),
  me: () => request<User>("/auth/me"),
  logout: () => request<void>("/auth/logout", { method: "POST" }),
  overview: () => request<Overview>("/overview"),
  jobs: () => request<Job[]>("/jobs"),
  posts: (params: Record<string, string | number | undefined>) =>
    request<ContentPage>(`/posts${queryString(params)}`),
  comments: (params: Record<string, string | number | undefined>) =>
    request<ContentPage>(`/comments${queryString(params)}`),
  sources: () => request<Source[]>("/sources"),
  syncSources: () => request<Source[]>("/sources/sync", { method: "POST" }),
  connections: () => request<Connection[]>("/connections"),
  browserAgents: () => request<BrowserAgent[]>("/browser-agents"),
  createBrowserAgentPairingCode: () =>
    request<BrowserAgentPairingCode>("/browser-agents/pairing-codes", {
      method: "POST",
    }),
  revokeBrowserAgent: (id: string) =>
    request<void>(`/browser-agents/${id}`, { method: "DELETE" }),
  connect: (platform: string) =>
    request<ConnectionResult>(`/connections/${platform}/connect`, {
      method: "POST",
    }),
  disconnect: (platform: string) =>
    request<ConnectionResult>(`/connections/${platform}/disconnect`, {
      method: "POST",
    }),
  runConfigurations: () =>
    request<RunConfiguration[]>("/run-configurations"),
  createRunConfiguration: (payload: {
    connection_id: string;
    source_id: string;
    max_posts: number;
  }) =>
    request<RunConfiguration>("/run-configurations", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  deleteRunConfiguration: (id: string) =>
    request<void>(`/run-configurations/${id}`, { method: "DELETE" }),
  runConfiguration: (id: string) =>
    request<Job>(`/run-configurations/${id}/run-now`, { method: "POST" }),
  collectFacebook: () =>
    request<Job>("/collection/facebook/run-now", { method: "POST" }),
};
