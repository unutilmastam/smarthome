import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import type { ReactElement } from "react";
import type { Device, Value } from "../api/types";
import { useSession } from "../auth/session";

export type Handler = (url: string, init: RequestInit) => { status?: number; body: unknown } | undefined;

export function mockFetch(handler: Handler) {
  const calls: { url: string; method: string; body: unknown }[] = [];
  globalThis.fetch = (async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const url = String(input);
    calls.push({ url, method: init.method ?? "GET", body: init.body ? JSON.parse(String(init.body)) : undefined });
    const res = handler(url, init) ?? { status: 404, body: { data: null, error: { code: "NOT_FOUND", message: "nf" } } };
    return new Response(JSON.stringify(res.body), { status: res.status ?? 200, headers: { "Content-Type": "application/json" } });
  }) as typeof fetch;
  return calls;
}

export const ok = (data: unknown) => ({ body: { data, error: null, meta: {} } });
export const err = (status: number, code: string) => ({ status, body: { data: null, error: { code, message: code }, meta: {} } });

export function renderWithProviders(ui: ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}><MemoryRouter>{ui}</MemoryRouter></QueryClientProvider>);
}

export function setMe(hasPin = true) {
  useSession.setState({ status: "authenticated", me: { id: "u1", email: "o@x.uz", name: "O", has_pin: hasPin } });
}

export const v = (value: unknown, extra: Partial<Value> = {}): Value =>
  ({ value, source: "reported", quality: "good", ts: "2026-10-07T12:00:00Z", ...extra });
export const unknown = (): Value => ({ value: null, source: "reported", quality: "unknown", ts: null });

export function device(caps: Device["capabilities"], over: Partial<Device> = {}): Device {
  return {
    id: "d1", home_id: "h1", room_id: null, key: "dev", name: "Qurilma", adapter: "esphome",
    protocol: "mqtt", model: null, enabled: true, unsupported: [],
    availability: { status: "online", ts: null }, hub_online: true, capabilities: caps, ...over,
  };
}

export const cap = (permission: string, risk: "low" | "medium" | "high", attributes: Record<string, Value>, config = {}) =>
  ({ permission, risk, config, attributes });
