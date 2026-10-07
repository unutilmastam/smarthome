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
export function hasFeedback(capability: string): boolean {
  return capability !== "climate";
}
