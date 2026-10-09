/**
 * Compact device tile (home screen, rooms, device list), in the style of the phone apps people
 * know: the round icon is the main control, the name opens the device. It shows the REPORTED
 * state only; while a command is in flight the icon spins, and an unknown state is never shown
 * as "off" (there is nothing to flip from, so two explicit buttons appear instead).
 */
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { Device, Role, Value } from "../api/types";
import { actionLabel, can } from "../lib/contracts";
import { usePrefs } from "../lib/prefs";
import { formatValue, valueBadge } from "../lib/status";
import { deviceVisual } from "../lib/visual";
import { CommandStatus } from "./CommandStatus";
import { useDeviceSend } from "./DeviceControls";
import { Icon } from "./Icon";

const known = (v?: Value) => !!v && (v.quality === "good" || v.quality === "stale");
const bool = (v?: Value) => (known(v) && typeof v!.value === "boolean" ? (v!.value as boolean) : null);

/** The one value a tile is about: [capability, attribute, how to format it]. */
const MAIN: [string, string, string][] = [
  ["alarm", "state", "alarm_state"], ["cover", "state", "state"], ["lock", "locked", "locked"],
  ["valve", "open", "open"], ["climate", "power", "power"], ["breaker", "closed", "closed"],
  ["contactor", "aux_contact_closed", "aux_contact_closed"], ["switch", "on", "on"],
  ["leak", "wet", "wet"], ["motion", "detected", "detected"], ["contact", "open", "open"],
  ["power_meter", "power", "power"], ["environment", "temperature", "temperature"],
  ["camera", "stream_available", "stream_available"],
];

/** Switch-like capabilities: the icon itself toggles them. */
const TOGGLE: Record<string, { attr: string; on: [string, Record<string, unknown>?]; off: [string, Record<string, unknown>?] }> = {
  switch: { attr: "on", on: ["turn_on"], off: ["turn_off"] },
  climate: { attr: "power", on: ["set_power", { power: true }], off: ["set_power", { power: false }] },
  contactor: { attr: "aux_contact_closed", on: ["close"], off: ["open"] },
  breaker: { attr: "closed", on: ["close"], off: ["open"] },
};

/** A second, smaller value next to the main one (brightness, room temperature, power). */
function extra(d: Device, t: (k: string) => string): string | null {
  const c = d.capabilities;
  const pick = (cap: string, attr: string) => (known(c[cap]?.attributes[attr]) ? formatValue(c[cap].attributes[attr], t, attr) : null);
  if (c.climate) return pick("climate", "current_temp");
  if (c.dimmer && bool(c.switch?.attributes.on) !== false) return pick("dimmer", "brightness");
  if (c.environment) return pick("environment", "humidity");
  if (c.power_meter && !MAIN.slice(0, 11).some(([cap]) => c[cap])) return null;
  if (c.power_meter) return pick("power_meter", "power");
  return null;
}

export function DeviceTile({ device, role }: { device: Device; role?: Role }) {
  const { t } = useTranslation();
  const { pinned, togglePin } = usePrefs();
  const isPinned = (pinned[device.home_id] ?? []).includes(device.id);
  const v = deviceVisual(device);
  const { doSend, tracked, busy, pendingFor, pinUi } = useDeviceSend(device);
  const offline = !device.hub_online || device.availability.status === "offline" || !device.enabled;
  const c = device.capabilities;

  const main = MAIN.find(([cap]) => c[cap]);
  const mainVal = main ? c[main[0]].attributes[main[1]] : undefined;
  const mainLabel = main ? t(`attr.${main[1]}`) : "";
  const pending = main ? pendingFor(main[0]) : false;
  const kind = valueBadge(mainVal, pending);
  const toggleCap = Object.keys(TOGGLE).find((cap) => c[cap]);
  const tripped = c.breaker?.attributes.tripped?.value === true;
  const allowed = (cap: string) => can(role, c[cap].permission);
  const disabledFor = (cap: string) => !allowed(cap) || busy || offline || (cap === "breaker" && tripped);
  const more = extra(device, t);

  let control: JSX.Element;
  if (toggleCap) {
    const spec = TOGGLE[toggleCap];
    const on = bool(c[toggleCap].attributes[spec.attr]);
    const go = (a: [string, Record<string, unknown>?]) => doSend(toggleCap, a[0], a[1]);
    control = on === null
      ? <span className="td-ico" aria-hidden="true"><Icon name={v.icon} size={24} /></span>
      : (
        <button type="button" role="switch" aria-checked={on} aria-label={`${device.name}: ${t(`cap.${toggleCap}`)}`}
          className="td-ico" data-pending={pendingFor(toggleCap) || undefined} disabled={disabledFor(toggleCap)}
          onClick={() => go(on ? spec.off : spec.on)}>
          <Icon name={v.icon} size={24} />
        </button>
      );
  } else {
    control = <span className="td-ico" aria-hidden="true" data-pending={pending || undefined}><Icon name={v.icon} size={24} /></span>;
  }

  // Explicit actions where a single tap would be a guess (unknown state) or is not on/off.
  const pills: { cap: string; action: string; icon: string }[] = [];
  if (toggleCap && bool(c[toggleCap].attributes[TOGGLE[toggleCap].attr]) === null && !offline) {
    pills.push({ cap: toggleCap, action: TOGGLE[toggleCap].on[0], icon: "power" },
      { cap: toggleCap, action: TOGGLE[toggleCap].off[0], icon: "stop" });
  }
  if (c.cover) pills.push({ cap: "cover", action: "open", icon: "up" }, { cap: "cover", action: "stop", icon: "stop" },
    { cap: "cover", action: "close", icon: "down" });
  if (c.lock) {
    const l = bool(c.lock.attributes.locked);
    if (l !== false) pills.push({ cap: "lock", action: "unlock", icon: "unlock" });
    if (l !== true) pills.push({ cap: "lock", action: "lock", icon: "lock" });
  }
  if (c.valve && bool(c.valve.attributes.open) === true) pills.push({ cap: "valve", action: "close", icon: "stop" });

  const sendPill = (p: { cap: string; action: string }) => {
    const spec = TOGGLE[p.cap];
    const params = spec && p.action === spec.on[0] ? spec.on[1] : spec && p.action === spec.off[0] ? spec.off[1] : undefined;
    doSend(p.cap, p.action, params);
  };

  const cls = ["dtile", `tone-${v.tone}`, v.active ? "on" : "", v.offline ? "offline" : "",
    v.anim ? `anim-${v.anim}` : "", tripped ? "alert" : ""].filter(Boolean).join(" ");
  return (
    <article className={cls} data-testid={`device-${device.key}`} data-active={v.active === null ? "unknown" : String(v.active)}>
      <div className="td-top">
        {control}
        <button className="td-star" aria-pressed={isPinned} aria-label={isPinned ? t("dashboard.unpin") : t("dashboard.pin")}
          onClick={() => togglePin(device.home_id, device.id)}>
          <Icon name="star" size={16} fill={isPinned ? "currentColor" : "none"} />
        </button>
      </div>
      <Link className="td-name" to={`/devices/${device.id}`}>{device.name}</Link>
      <div className="td-state" data-testid={`value-${mainLabel}`}>
        <span className={known(mainVal) ? "" : "dim"}>
          {offline ? t("availability.offline") : tripped ? t("panel.tripped") : formatValue(mainVal, t, main?.[2])}
        </span>
        {more && !offline && <span className="td-more">· {more}</span>}
        <span className={`td-q q-${kind}`} title={t(`status.${kind}`)}>
          <span className="sr-only">{t(`status.${kind}`)}</span>
        </span>
      </div>
      {pills.length > 0 && (
        <div className="td-pills">
          {pills.map((p) => (
            <button key={p.cap + p.action} type="button" aria-label={actionLabel(t, p.cap, p.action)}
              title={actionLabel(t, p.cap, p.action)} disabled={disabledFor(p.cap)} onClick={() => sendPill(p)}>
              <Icon name={p.icon} size={16} />
            </button>
          ))}
        </div>
      )}
      <CommandStatus tracked={tracked} compact />
      {pinUi}
    </article>
  );
}
