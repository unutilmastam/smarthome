export type Quality = "good" | "stale" | "unknown" | "not_supported";
export type Source = "reported" | "assumed" | "computed";

export interface Value {
  value: unknown;
  unit?: string;
  source: Source;
  quality: Quality;
  ts: string | null;
}

export interface CapabilityView {
  permission: string;
  risk: "low" | "medium" | "high";
  config: Record<string, unknown>;
  attributes: Record<string, Value>;
}

export interface Device {
  id: string;
  home_id: string;
  room_id: string | null;
  key: string;
  name: string;
  adapter: string;
  protocol: string;
  model: string | null;
  /** UI icon key chosen by the owner; null = derived from capabilities. */
  icon?: string | null;
  enabled: boolean;
  unsupported: string[];
  availability: { status: "online" | "offline" | "unknown"; ts: string | null };
  hub_online: boolean;
  capabilities: Record<string, CapabilityView>;
}

export type Role = "owner" | "admin" | "family" | "guest" | "viewer";

export interface Home {
  id: string;
  name: string;
  timezone: string;
  latitude: number | null;
  longitude: number | null;
  my_role: Role;
  tariff_per_kwh: number | null;
  currency: string;
}

export interface EnergyDevice { device_id: string; key: string; name: string; kwh: number; cost: number | null; currency: string | null; days_with_data: number }
export interface EnergySummary {
  period: "day" | "month"; from: string; to: string; timezone: string;
  tariff_per_kwh: number | null; currency: string; total_kwh: number | null; total_cost: number | null;
  devices: EnergyDevice[];
}
export interface TelemetryPoint { ts: string; avg: number; min: number; max: number; last: number }

export interface Room { id: string; home_id: string; name: string; type: "indoor" | "outdoor"; floor_id: string | null; icon?: string | null }

export interface Hub {
  id: string; name: string; status: "active" | "revoked"; online: boolean;
  last_seen: string | null; version: string | null;
}

export type CommandStatus =
  | "queued" | "sent" | "acked" | "confirmed" | "rejected" | "failed" | "expired" | "timeout";

export interface CommandEvent { ts: string; status: string; source: string; applied: boolean; reason: string | null; detail: string | null }

export interface Command {
  id: string; device_id: string; capability: string; action: string;
  params: Record<string, unknown>; status: CommandStatus; reason: string | null;
  detail: string | null; risk: string; created_at: string; events?: CommandEvent[];
}

export interface Member { user_id: string; email: string; name: string; role: Role }

export interface SessionInfo { id: string; current: boolean; ip: string | null; user_agent: string | null; last_used_at: string }

export interface ApiErrorBody { code: string; message: string; details?: unknown }
