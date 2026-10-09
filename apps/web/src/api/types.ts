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
  /** Devices that are not ours (ADR 0016), e.g. Tuya: profile, device_id, ip, version. */
  connection?: { profile?: string; device_id?: string; ip?: string; version?: string; [k: string]: unknown } | null;
  /** The secret itself (Tuya Local Key) is never sent to the app. */
  has_secret?: boolean;
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
/** Automation rule (packages/contracts/schemas/automation.schema.json, ADR 0013). */
export type Trigger =
  | { type: "state"; device: string; capability: string; attribute: string; to: unknown; for_s?: number }
  | { type: "time"; at: string; days?: string[] }
  | { type: "sun"; event: "sunrise" | "sunset"; offset_min?: number; days?: string[] };
export type Condition =
  | { type: "state"; device: string; capability: string; attribute: string; is: unknown }
  | { type: "time"; after: string; before: string; days?: string[] }
  | { type: "sun"; is: "day" | "night"; offset_min?: number }
  | { type: "security_mode"; is: string[] };
export type AutoAction =
  | { type: "command"; device: string; capability: string; action: string; params?: Record<string, unknown>; auto_off_after_s?: number }
  | { type: "delay"; seconds: number }
  | { type: "notify"; text: string; severity?: "info" | "warning" | "critical" };
export interface AutomationDef {
  triggers: Trigger[]; conditions?: Condition[]; actions: AutoAction[];
  cooldown_s?: number; max_runs_per_hour?: number; manual_override_s?: number;
}
export interface AutomationRun {
  id: string; automation_id: string; version: number; ts: string; trigger: string;
  result: "ok" | "partial" | "failed" | "skipped"; reason: string | null;
  actions: { type: string; device?: string; action?: string; outcome: string; text?: string; severity?: string }[];
}
export interface Automation {
  id: string; home_id: string; name: string; enabled: boolean; definition: AutomationDef;
  version: number; created_at: string; updated_at: string; last_run: AutomationRun | null;
}

/** Event from a device or the hub (ADR 0012). */
export interface HomeEvent {
  id: string; ts: string; type: string; severity: "info" | "warning" | "critical";
  device_id: string | null; device_key: string; device_name: string | null; data: Record<string, unknown>;
}

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
  /** Exactly what the hub last reported (Faza 14); missing keys = unknown. */
  health?: { mqtt_connected?: boolean; data_disk_pct?: number; data_disk_warning?: boolean;
    disk_usage_pct?: number; disk_warning?: boolean; outbox?: number } | null;
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

/** ADR 0014: a notification and who acknowledged it. */
export interface AppNotification {
  id: string; ts: string; created_at: string; severity: "info" | "warning" | "critical";
  source: "event" | "automation" | "hub" | "device" | "test"; kind: string; title: string; body: string;
  data: Record<string, unknown>; needs_ack: boolean; acked_at: string | null; acked_by: string | null; acked_by_name: string | null;
}
export interface NotificationChannels {
  telegram: { available: boolean; links: { id: string; username: string | null; created_at: string }[] };
  push: { available: boolean; public_key: string | null;
    subscriptions: { id: string; endpoint: string; user_agent: string | null; created_at: string; last_success_at: string | null }[] };
}
export interface NotifyPrefs { notify_min_severity: "info" | "warning" | "critical"; receives: boolean }
export interface TelegramLinkCode { code: string; expires_at: string; bot_username: string | null; url: string | null }
