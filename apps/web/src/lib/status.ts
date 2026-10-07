import type { CommandStatus, Value } from "../api/types";

export type BadgeKind = "ok" | "pending" | "assumed" | "stale" | "unknown" | "unsupported" | "failed";

/** ARCHITECTURE 4.2: ✓ confirmed, ⏳ pending, ≈ assumed, ⚠ stale, ? unknown. */
export function valueBadge(v: Value | undefined, pending = false): BadgeKind {
  if (pending) return "pending";
  if (!v || v.quality === "unknown") return "unknown";
  if (v.quality === "not_supported") return "unsupported";
  if (v.quality === "stale") return "stale";
  if (v.source === "assumed") return "assumed";
  return "ok";
}

export const BADGE_ICON: Record<BadgeKind, string> = {
  ok: "✓", pending: "⏳", assumed: "≈", stale: "⚠", unknown: "?", unsupported: "—", failed: "✕",
};

export const TERMINAL: CommandStatus[] = ["confirmed", "rejected", "failed", "expired", "timeout"];

export function commandBadge(status: CommandStatus): BadgeKind {
  if (status === "confirmed") return "ok";
  if (status === "acked") return "pending";
  if (["queued", "sent"].includes(status)) return "pending";
  return "failed";
}

/** Displays a value WITHOUT inventing anything: unknown/not_supported have no number. */
export type T = (k: string, o?: Record<string, unknown>) => string;

export function formatValue(v: Value | undefined, t: T, attr?: string): string {
  if (v?.quality === "not_supported") return t("status.unsupported");
  if (!v || v.quality === "unknown" || v.value === null || v.value === undefined) return "—";
  const x = v.value;
  if (typeof x === "boolean") {
    const plain = x ? t("value.on") : t("value.off");
    // Attribute-specific words ("To'silgan", "Harakat bor") instead of a generic on/off.
    return attr ? t(`bool.${attr}.${x}`, { defaultValue: plain }) : plain;
  }
  if (typeof x === "number") return `${Number.isInteger(x) ? x : x.toFixed(2).replace(/\.?0+$/, "")}${v.unit ? " " + v.unit : ""}`;
  if (Array.isArray(x)) return x.join(", ");
  return t(`enum.${String(x)}`, { defaultValue: String(x) });
}
