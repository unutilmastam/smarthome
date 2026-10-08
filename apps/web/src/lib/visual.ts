/**
 * How a device LOOKS, derived only from reported/assumed values (never from what was
 * requested). Unknown values give a neutral look, not "off".
 */
import type { Device, Value } from "../api/types";
import { hasIcon } from "../components/Icon";

export type Tone = "light" | "gate" | "cool" | "water" | "power" | "alert" | "sensor" | "camera" | "neutral";

export interface Visual {
  icon: string;
  tone: Tone;
  /** true = "on/open/active" by REPORTED state; null = unknown. */
  active: boolean | null;
  /** extra animation class: moving, flowing, spinning, pulse */
  anim?: "moving" | "flowing" | "spinning" | "pulse";
  offline: boolean;
}

const val = (v?: Value) => (v && (v.quality === "good" || v.quality === "stale") ? v.value : undefined);

export function deviceVisual(d: Device): Visual {
  const v = derivedVisual(d);
  // The owner's icon choice only changes the picture; lock keeps its live locked/unlocked icon.
  if (hasIcon(d.icon) && !(d.capabilities.lock && d.icon === "lock")) return { ...v, icon: d.icon };
  return v;
}

function derivedVisual(d: Device): Visual {
  const c = d.capabilities;
  const offline = !d.hub_online || d.availability.status === "offline";
  const base = { offline };
  if (c.alarm) {
    const st = val(c.alarm.attributes.state) as string | undefined;
    const alarm = st === "triggered" || st === "pending";
    return { ...base, icon: "shield", tone: alarm ? "alert" : st?.startsWith("armed") ? "power" : "neutral",
      active: st === undefined ? null : st !== "disarmed", anim: alarm || st === "arming" ? "pulse" : undefined };
  }
  if (c.cover) {
    const st = val(c.cover.attributes.state) as string | undefined;
    const moving = st === "opening" || st === "closing";
    return { ...base, icon: "gate", tone: "gate", active: st === undefined ? null : st !== "closed",
      anim: moving ? "moving" : undefined };
  }
  if (c.lock) {
    const l = val(c.lock.attributes.locked);
    return { ...base, icon: l === false ? "unlock" : "lock", tone: "gate", active: l === undefined ? null : l === false };
  }
  if (c.valve) {
    const o = val(c.valve.attributes.open);
    return { ...base, icon: "drop", tone: "water", active: o === undefined ? null : !!o, anim: o ? "flowing" : undefined };
  }
  if (c.climate) {
    const p = val(c.climate.attributes.power);
    return { ...base, icon: "ac", tone: "cool", active: p === undefined ? null : !!p, anim: p ? "spinning" : undefined };
  }
  if (c.breaker) {
    const closed = val(c.breaker.attributes.closed);
    const tripped = val(c.breaker.attributes.tripped) === true;
    return { ...base, icon: "breaker", tone: tripped ? "alert" : "power",
      active: closed === undefined ? null : !!closed, anim: tripped ? "pulse" : undefined };
  }
  if (c.contactor) {
    const a = val(c.contactor.attributes.aux_contact_closed);
    return { ...base, icon: "power", tone: "power", active: a === undefined ? null : !!a };
  }
  if (c.switch) {
    const on = val(c.switch.attributes.on);
    return { ...base, icon: "bulb", tone: "light", active: on === undefined ? null : !!on };
  }
  if (c.leak) {
    const w = val(c.leak.attributes.wet);
    return { ...base, icon: "leak", tone: w ? "alert" : "sensor", active: w === undefined ? null : !!w, anim: w ? "pulse" : undefined };
  }
  if (c.motion) {
    const m = val(c.motion.attributes.detected);
    return { ...base, icon: "motion", tone: m ? "alert" : "sensor", active: m === undefined ? null : !!m, anim: m ? "pulse" : undefined };
  }
  if (c.contact) {
    const o = val(c.contact.attributes.open);
    return { ...base, icon: "door", tone: "sensor", active: o === undefined ? null : !!o };
  }
  if (c.power_meter) {
    const w = val(c.power_meter.attributes.power);
    return { ...base, icon: "energy", tone: "power", active: typeof w === "number" ? w > 5 : null };
  }
  if (c.environment) return { ...base, icon: "thermo", tone: "sensor", active: null };
  if (c.camera) {
    const s = val(c.camera.attributes.stream_available);
    return { ...base, icon: "camera", tone: "camera", active: s === undefined ? null : !!s };
  }
  return { ...base, icon: "devices", tone: "neutral", active: null };
}
