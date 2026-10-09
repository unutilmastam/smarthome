/** Helpers for the automation editor/list (ADR 0013). Pure: no network, no guessing. */
import type { AutoAction, AutomationDef, Condition, Device, Trigger } from "../api/types";
import { CAPABILITIES, type AttrSpec } from "./contracts";

type T = (k: string, o?: Record<string, unknown>) => string;

export const DAYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"] as const;

/** Attributes a rule can watch: booleans, enums and numbers that the device really has. */
export function watchable(d: Device): { cap: string; attr: string; spec: AttrSpec }[] {
  const out: { cap: string; attr: string; spec: AttrSpec }[] = [];
  for (const cap of Object.keys(d.capabilities)) {
    for (const [attr, spec] of Object.entries(CAPABILITIES[cap]?.attributes ?? {})) {
      if (d.unsupported.includes(`${cap}.${attr}`)) continue;
      if (["boolean", "number", "integer"].includes(spec.type) || spec.enum) out.push({ cap, attr, spec });
    }
  }
  return out;
}

/** Actions an AUTOMATION may run: high-risk capabilities need a person with a PIN. */
export function automatable(d: Device): { cap: string; action: string }[] {
  const out: { cap: string; action: string }[] = [];
  // On/off first: it is what most rules do.
  const caps = Object.keys(d.capabilities).sort((a, b) => Number(b === "switch") - Number(a === "switch"));
  for (const cap of caps) {
    const spec = CAPABILITIES[cap];
    if (!spec || spec.risk === "high") continue;
    for (const action of Object.keys(spec.actions)) out.push({ cap, action });
  }
  return out;
}

export function defaultValue(spec?: AttrSpec): unknown {
  if (!spec) return true;
  if (spec.type === "boolean") return true;
  if (spec.enum) return spec.enum[0];
  return spec.minimum ?? 0;
}

export function valueLabel(t: T, attr: string, spec: AttrSpec | undefined, v: unknown): string {
  if (typeof v === "boolean") return t(`bool.${attr}.${v}`, { defaultValue: v ? t("value.on") : t("value.off") });
  if (typeof v === "string") return t(`enum.${v}`, { defaultValue: v });
  return `${String(v)}${spec?.unit ? " " + spec.unit : ""}`;
}

const name = (devices: Device[], key: string) => devices.find((d) => d.key === key)?.name ?? key;

export function describeTrigger(t: T, tr: Trigger, devices: Device[]): string {
  if (tr.type === "state") {
    const spec = CAPABILITIES[tr.capability]?.attributes[tr.attribute];
    return `${name(devices, tr.device)}: ${valueLabel(t, tr.attribute, spec, tr.to)}`;
  }
  if (tr.type === "time") return t("auto.at", { time: tr.at });
  const off = tr.offset_min ?? 0;
  return t(`auto.${tr.event}`) + (off ? ` ${off > 0 ? "+" : ""}${off} ${t("auto.min")}` : "");
}

export function describeCondition(t: T, c: Condition, devices: Device[]): string {
  if (c.type === "state") {
    const spec = CAPABILITIES[c.capability]?.attributes[c.attribute];
    return `${name(devices, c.device)}: ${valueLabel(t, c.attribute, spec, c.is)}`;
  }
  if (c.type === "time") return `${c.after}–${c.before}`;
  if (c.type === "sun") return t(`auto.${c.is}`);
  return c.is.map((s) => t(`enum.${s}`)).join(" / ");
}

export function describeAction(t: T, a: AutoAction, devices: Device[]): string {
  if (a.type === "command") return `${name(devices, a.device)}: ${t(`action.${a.action}`)}`;
  if (a.type === "delay") return t("auto.wait", { s: a.seconds });
  return `🔔 ${a.text}`;
}

export function summary(t: T, d: AutomationDef, devices: Device[]): string {
  const when = d.triggers.map((x) => describeTrigger(t, x, devices)).join(` ${t("auto.or")} `);
  const iff = (d.conditions ?? []).map((x) => describeCondition(t, x, devices)).join(", ");
  const then = d.actions.map((x) => describeAction(t, x, devices)).join(", ");
  return `${when}${iff ? ` (${iff})` : ""} → ${then}`;
}

export const triggerIcon = (d: AutomationDef) => {
  const tr = d.triggers[0];
  return tr?.type === "time" ? "clock" : tr?.type === "sun" ? (tr.event === "sunset" ? "moon" : "sun") : "motion";
};
