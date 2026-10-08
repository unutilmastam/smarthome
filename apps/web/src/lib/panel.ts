/** Electrical panel layout (ADR 0015). Pure: what the breakers report, nothing invented. */
import type { Device, Value } from "../api/types";

export type LeverState = "on" | "off" | "tripped" | "unknown";

export const good = (v?: Value) => !!v && (v.quality === "good" || v.quality === "stale");

export interface BreakerInfo {
  device: Device; panel: string; position: number | null; poles: number;
  rating: string | null; state: LeverState; power: Value | undefined; duplicate: boolean;
}

export function breakerInfo(d: Device): Omit<BreakerInfo, "duplicate"> {
  const b = d.capabilities.breaker;
  const cfg = b.config as { panel?: string; position?: number; poles?: number; rating_a?: number; curve?: string };
  const closed = b.attributes.closed;
  const tripped = b.attributes.tripped;
  let state: LeverState = "unknown";
  if (good(tripped) && tripped!.value === true) state = "tripped";
  else if (good(closed) && typeof closed!.value === "boolean") state = closed!.value ? "on" : "off";
  return {
    device: d,
    panel: cfg.panel?.trim() || "",
    position: typeof cfg.position === "number" ? cfg.position : null,
    poles: cfg.poles ?? 1,
    rating: cfg.rating_a ? `${cfg.curve ?? ""}${cfg.rating_a}` : null,
    state,
    power: d.capabilities.power_meter?.attributes.power,
  };
}

/** Breakers grouped by panel, each panel ordered left-to-right by label number. */
export function groupPanels(devices: Device[]): { panel: string; items: BreakerInfo[] }[] {
  const byPanel = new Map<string, Omit<BreakerInfo, "duplicate">[]>();
  for (const d of devices) {
    if (!d.capabilities?.breaker) continue;
    const info = breakerInfo(d);
    byPanel.set(info.panel, [...(byPanel.get(info.panel) ?? []), info]);
  }
  return [...byPanel.entries()]
    .sort(([a], [b]) => (a === "" ? -1 : b === "" ? 1 : a.localeCompare(b)))
    .map(([panel, list]) => {
      const counts = new Map<number, number>();
      for (const i of list) if (i.position !== null) counts.set(i.position, (counts.get(i.position) ?? 0) + 1);
      const items = list
        .map((i) => ({ ...i, duplicate: i.position !== null && (counts.get(i.position) ?? 0) > 1 }))
        .sort((a, b) => (a.position ?? 1e9) - (b.position ?? 1e9) || a.device.name.localeCompare(b.device.name));
      return { panel, items };
    });
}

export function nextPosition(items: BreakerInfo[]): number {
  const used = new Set(items.map((i) => i.position));
  let n = 1;
  while (used.has(n)) n++;
  return n;
}

