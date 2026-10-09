/**
 * Device types the owner can add from the UI. A type is only a preset of contract
 * capabilities (packages/contracts/capabilities.json) plus a default icon; the backend
 * validates the capabilities as usual. Nothing here invents a device state.
 */
import type { Room } from "../api/types";

export interface DeviceType {
  id: string;
  icon: string;
  /** null = "custom": the user picks capabilities. */
  caps: string[] | null;
  /** Smart Life / Tuya device (ADR 0016): the hub profile; the profile decides the capabilities. */
  tuya?: "switch" | "plug_meter" | "breaker" | "light" | "ir";
  /** IR remote layout drawn by the app. */
  layout?: "tv" | "ac";
}

/** Off-the-shelf Wi-Fi devices (Smart Life / Tuya), reached by the hub on the home LAN. */
export const TUYA_TYPES: DeviceType[] = [
  { id: "tuya_breaker", icon: "breaker", caps: ["breaker", "power_meter"], tuya: "breaker" },
  { id: "tuya_relay", icon: "power", caps: ["switch"], tuya: "switch" },
  { id: "tuya_plug", icon: "socket", caps: ["switch", "power_meter"], tuya: "plug_meter" },
  { id: "tuya_light", icon: "bulb", caps: ["switch", "dimmer"], tuya: "light" },
  { id: "ir_tv", icon: "tv", caps: ["remote"], tuya: "ir", layout: "tv" },
  { id: "ir_ac", icon: "ac", caps: ["remote"], tuya: "ir", layout: "ac" },
];

export const DEVICE_TYPES: DeviceType[] = [
  { id: "light", icon: "bulb", caps: ["switch"] },
  { id: "dimmer", icon: "lamp", caps: ["switch", "dimmer"] },
  { id: "socket", icon: "socket", caps: ["switch"] },
  { id: "fan", icon: "fan", caps: ["switch"] },
  { id: "boiler", icon: "boiler", caps: ["switch"] },
  { id: "ac", icon: "ac", caps: ["climate"] },
  { id: "gate", icon: "gate", caps: ["cover"] },
  { id: "garage", icon: "garage", caps: ["cover"] },
  { id: "curtain", icon: "curtain", caps: ["cover"] },
  { id: "lock", icon: "lock", caps: ["lock"] },
  { id: "irrigation", icon: "sprinkler", caps: ["valve"] },
  { id: "meter", icon: "meter", caps: ["power_meter"] },
  { id: "breaker", icon: "breaker", caps: ["breaker"] },
  { id: "contactor", icon: "power", caps: ["contactor"] },
  { id: "siren", icon: "siren", caps: ["switch"] },
  { id: "motion", icon: "motion", caps: ["motion"] },
  { id: "door", icon: "door", caps: ["contact"] },
  { id: "leak", icon: "leak", caps: ["leak"] },
  { id: "climate_sensor", icon: "thermo", caps: ["environment"] },
  { id: "camera", icon: "camera", caps: ["camera"] },
  { id: "custom", icon: "devices", caps: null },
];

/** Icons the owner can choose for a device. */
export const DEVICE_ICONS = [
  "bulb", "lamp", "ceiling", "socket", "plug", "fan", "ac", "heater", "boiler", "tv", "fridge",
  "washer", "speaker", "pump", "sprinkler", "drop", "gate", "garage", "door", "window", "curtain",
  "lock", "bell", "siren", "motion", "leak", "thermo", "meter", "breaker", "power", "energy", "solar",
  "charger", "car", "camera", "hub", "devices",
];

/** Icons the owner can choose for a room (section). */
export const ROOM_ICONS = [
  "sofa", "bed", "kitchen", "dining", "bath", "kids", "office", "gym", "stairs", "storage",
  "garage", "balcony", "plant", "pool", "door", "home", "rooms",
];

export const roomIcon = (r: Pick<Room, "icon" | "type">) =>
  r.icon || (r.type === "outdoor" ? "plant" : "rooms");

const TRANSLIT: [RegExp, string][] = [
  [/[ʻʼ'`’‘]/g, ""],
  [/а/g, "a"], [/б/g, "b"], [/в/g, "v"], [/г/g, "g"], [/д/g, "d"], [/е|ё|э/g, "e"], [/ж/g, "j"],
  [/з/g, "z"], [/и|й/g, "i"], [/к/g, "k"], [/л/g, "l"], [/м/g, "m"], [/н/g, "n"], [/о/g, "o"],
  [/п/g, "p"], [/р/g, "r"], [/с/g, "s"], [/т/g, "t"], [/у|ў/g, "u"], [/ф/g, "f"], [/х|ҳ/g, "x"],
  [/ц/g, "ts"], [/ч/g, "ch"], [/ш|щ/g, "sh"], [/ы/g, "i"], [/ю/g, "yu"], [/я/g, "ya"], [/қ/g, "q"],
  [/ғ/g, "g"],
];

/**
 * Suggests a device key (backend pattern ^[a-z][a-z0-9_]{1,63}$) from a display name.
 * The key must match the firmware's device_key, so the user can still edit it.
 */
export function suggestKey(name: string, taken: string[] = []): string {
  let s = name.toLowerCase();
  for (const [re, to] of TRANSLIT) s = s.replace(re, to);
  s = s.normalize("NFKD").replace(/[̀-ͯ]/g, "").replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
  if (!/^[a-z]/.test(s)) s = `device_${s}`.replace(/_+$/, "");
  s = s.slice(0, 48).replace(/_+$/, "");
  if (s.length < 2) s = "device";
  let out = s;
  for (let i = 2; taken.includes(out); i += 1) out = `${s}_${i}`;
  return out;
}

export const KEY_RE = /^[a-z][a-z0-9_]{1,63}$/;
