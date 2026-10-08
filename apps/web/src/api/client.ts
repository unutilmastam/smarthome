/**
 * API client (ADR 0009): the access token lives only in memory; the refresh token is an
 * HttpOnly cookie the browser sends to /api/v1/auth. Every auth call carries X-Client: web.
 */
import type { ApiErrorBody } from "./types";

const BASE = "/api/v1";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public details?: unknown) {
    super(message);
  }
}

let accessToken: string | null = null;
let refreshing: Promise<boolean> | null = null;
let onSessionLost: () => void = () => {};

export function setAccessToken(token: string | null) { accessToken = token; }
export function hasAccessToken() { return accessToken !== null; }
export function onLoggedOut(cb: () => void) { onSessionLost = cb; }

async function parse(res: Response) {
  let body: { data?: unknown; error?: ApiErrorBody | null; meta?: Record<string, unknown> } = {};
  try { body = await res.json(); } catch { /* empty body */ }
  if (!res.ok || body.error) {
    const e = body.error ?? { code: "HTTP_" + res.status, message: res.statusText };
    throw new ApiError(res.status, e.code, e.message, e.details);
  }
  return body as { data: unknown; meta: Record<string, unknown> };
}

export async function refreshSession(): Promise<boolean> {
  if (!refreshing) {
    refreshing = (async () => {
      try {
        const res = await fetch(`${BASE}/auth/refresh`, {
          method: "POST", credentials: "same-origin", headers: { "X-Client": "web" },
        });
        const body = await parse(res);
        setAccessToken((body.data as { access_token: string }).access_token);
        return true;
      } catch {
        setAccessToken(null);
        return false;
      } finally {
        setTimeout(() => { refreshing = null; }, 0);
      }
    })();
  }
  return refreshing;
}

export async function request<T>(method: string, path: string, body?: unknown, retry = true): Promise<{ data: T; meta: Record<string, unknown> }> {
  const headers: Record<string, string> = { "X-Client": "web" };
  if (body !== undefined) headers["Content-Type"] = "application/json";
  if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;
  const res = await fetch(BASE + path, {
    method, headers, credentials: "same-origin",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (res.status === 401 && retry && !path.startsWith("/auth/login")) {
    if (await refreshSession()) return request<T>(method, path, body, false);
    onSessionLost();
  }
  return (await parse(res)) as { data: T; meta: Record<string, unknown> };
}

export const api = {
  get: <T>(p: string) => request<T>("GET", p).then((r) => r.data),
  page: <T>(p: string) => request<T>("GET", p),
  post: <T>(p: string, b?: unknown) => request<T>("POST", p, b ?? {}).then((r) => r.data),
  patch: <T>(p: string, b: unknown) => request<T>("PATCH", p, b).then((r) => r.data),
  put: <T>(p: string, b: unknown) => request<T>("PUT", p, b).then((r) => r.data),
  del: <T>(p: string) => request<T>("DELETE", p).then((r) => r.data),
};
