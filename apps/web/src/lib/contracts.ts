/** Single source of truth shared with backend and hub (packages/contracts). */
import capabilitiesJson from "../../../../packages/contracts/capabilities.json";
import rolesJson from "../../../../packages/contracts/roles.json";
import type { Role } from "../api/types";

export interface AttrSpec { type: string; unit?: string; minimum?: number; maximum?: number; enum?: string[] }
export interface ActionSpec { params: { required?: string[]; properties?: Record<string, AttrSpec & { minimum?: number; maximum?: number }> } }
export interface CapSpec {
  title: string; permission: string; risk: "low" | "medium" | "high";
  attributes: Record<string, AttrSpec>; actions: Record<string, ActionSpec>; confirm_attribute?: string;
}

export const CAPABILITIES = (capabilitiesJson as unknown as { capabilities: Record<string, CapSpec> }).capabilities;
const ROLES = (rolesJson as unknown as { roles: Record<string, string[]> }).roles;

export function can(role: Role | undefined, permission: string): boolean {
  return !!role && (ROLES[role] ?? []).includes(permission);
}

/** Capabilities whose state proves a command (others stop at "acked"). */
export function hasFeedback(capability: string, action?: string): boolean {
  // IR: an assumed climate state and a remote button press are only ever "sent" (ADR 0016);
  // a learned remote button IS confirmed (the hub lists it once the code was captured).
  if (capability === "remote") return action === "learn" || action === "forget";
  // A relative step ("volume +1") has no target value to wait for.
  if (capability === "media") return !["volume_up", "volume_down", "channel_up", "channel_down"].includes(action ?? "");
  return capability !== "climate";
}

/** "close" is "Yopish" for a gate but "Yoqish" for a breaker: capability-specific label first. */
export function actionLabel(t: (k: string, o?: Record<string, unknown>) => string, cap: string, action: string): string {
  return t(`actionCap.${cap}.${action}`, { defaultValue: t(`action.${action}`) });
}
