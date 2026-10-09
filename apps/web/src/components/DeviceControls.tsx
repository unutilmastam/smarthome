import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { CapabilityView, Device, Role, Value } from "../api/types";
import { useCommand } from "../lib/commands";
import { CAPABILITIES, actionLabel, can, hasFeedback } from "../lib/contracts";
import { useSession } from "../auth/session";
import { useDevices } from "../api/hooks";
import { useCurrentHome } from "../lib/home";
import { formatValue } from "../lib/status";
import { CommandStatus } from "./CommandStatus";
import { Icon } from "./Icon";
import { PinDialog } from "./PinDialog";
import { MediaControl, RemoteControl } from "./RemoteControl";
import { ValueView } from "./ValueView";

type Send = (cap: string, action: string, params?: Record<string, unknown>) => void;

interface CtlProps { device: Device; cap: string; view: CapabilityView; send: Send; disabled: boolean; pending: boolean }

const attrLabel = (t: (k: string) => string, a: string) => t(`attr.${a}`);

/**
 * A real-looking power switch. The knob follows the REPORTED state only; while a command is
 * in flight the knob shows a spinner ring. When the state is unknown there is no "current"
 * side to flip from, so two explicit buttons are shown instead of guessing.
 */
export function PowerSwitch({ on, label, pending, disabled, onTurnOn, onTurnOff }: {
  on: boolean | null; label: string; pending: boolean; disabled: boolean; onTurnOn: () => void; onTurnOff: () => void;
}) {
  const { t } = useTranslation();
  if (on === null) {
    return (
      <div className="seg power-seg" data-state="unknown">
        <button disabled={disabled} onClick={onTurnOn}><Icon name="power" size={18} /> {t("action.turn_on")}</button>
        <button disabled={disabled} onClick={onTurnOff}><Icon name="power" size={18} /> {t("action.turn_off")}</button>
      </div>
    );
  }
  return (
    <button type="button" role="switch" aria-checked={on} aria-label={label} className="pswitch"
      data-state={on ? "on" : "off"} data-pending={pending} disabled={disabled}
      onClick={on ? onTurnOff : onTurnOn}>
      <span className="track" aria-hidden="true">
        <span className="lbl on">I</span><span className="lbl off">O</span>
        <span className="knob"><Icon name="power" size={18} strokeWidth={2.4} /></span>
      </span>
    </button>
  );
}

const reportedBool = (v?: Value) =>
  v && (v.quality === "good" || v.quality === "stale") && typeof v.value === "boolean" ? (v.value as boolean) : null;

function SwitchCtl({ cap, view, send, disabled, pending }: CtlProps) {
  const { t } = useTranslation();
  const v = view.attributes.on;
  return (
    <div className="sw-line">
      <ValueView attr="on" label={attrLabel(t, "on")} value={v} pending={pending} big />
      <PowerSwitch on={reportedBool(v)} label={t("cap.switch")} pending={pending} disabled={disabled}
        onTurnOn={() => send(cap, "turn_on")} onTurnOff={() => send(cap, "turn_off")} />
    </div>
  );
}

function DimmerCtl({ cap, view, send, disabled, pending }: CtlProps) {
  const { t } = useTranslation();
  const current = view.attributes.brightness;
  const known = typeof current?.value === "number" ? (current.value as number) : 50;
  const [draft, setDraft] = useState<number>(known);
  return (
    <>
      <ValueView attr="brightness" label={attrLabel(t, "brightness")} value={current} pending={pending} />
      <div className="row">
        <input type="range" min={0} max={100} value={draft} aria-label={t("attr.brightness")}
          onChange={(e) => setDraft(Number(e.target.value))} style={{ flex: 1 }} disabled={disabled} />
        <span style={{ minWidth: 44 }}>{draft}%</span>
        <button disabled={disabled} onClick={() => send(cap, "set_brightness", { brightness: draft })}>{t("action.set_brightness")}</button>
      </div>
    </>
  );
}

function ClimateCtl({ device, cap, view, send, disabled, pending }: CtlProps) {
  const { t } = useTranslation();
  const spec = CAPABILITIES.climate.attributes;
  const target = view.attributes.target_temp;
  const base = typeof target?.value === "number" ? (target.value as number) : 24;
  return (
    <>
      <ValueView attr="current_temp" label={attrLabel(t, "current_temp")} value={view.attributes.current_temp} big />
      <ValueView attr="power" label={attrLabel(t, "power")} value={view.attributes.power} pending={pending} />
      <ValueView attr="target_temp" label={attrLabel(t, "target_temp")} value={target} />
      <ValueView attr="mode" label={attrLabel(t, "mode")} value={view.attributes.mode} />
      {device.adapter !== "yandex" && <p className="muted" style={{ margin: 0 }}>{t("control.assumedNote")}</p>}
      <div className="sw-line">
        <span className="muted">{t("attr.power")}</span>
        <PowerSwitch on={reportedBool(view.attributes.power)} label={t("attr.power")} pending={pending} disabled={disabled}
          onTurnOn={() => send(cap, "set_power", { power: true })} onTurnOff={() => send(cap, "set_power", { power: false })} />
      </div>
      <div className="stepper">
        <button className="round" disabled={disabled || base <= (spec.target_temp.minimum ?? 16)} aria-label="-1°C"
          onClick={() => send(cap, "set_target_temp", { target_temp: base - 1 })}><Icon name="minus" /></button>
        <span className="temp"><Icon name="snow" size={18} /> {typeof target?.value === "number" ? `${base}°` : "—"}</span>
        <button className="round" disabled={disabled || base >= (spec.target_temp.maximum ?? 30)} aria-label="+1°C"
          onClick={() => send(cap, "set_target_temp", { target_temp: base + 1 })}><Icon name="plus" /></button>
      </div>
      <div className="row">
        <select aria-label={t("attr.mode")} disabled={disabled} defaultValue=""
          onChange={(e) => e.target.value && send(cap, "set_mode", { mode: e.target.value })}>
          <option value="" disabled>{t("attr.mode")}</option>
          {(spec.mode.enum ?? []).map((m) => <option key={m} value={m}>{t(`enum.${m}`)}</option>)}
        </select>
        <select aria-label={t("attr.fan")} disabled={disabled} defaultValue=""
          onChange={(e) => e.target.value && send(cap, "set_fan", { fan: e.target.value })}>
          <option value="" disabled>{t("attr.fan")}</option>
          {(spec.fan.enum ?? []).map((m) => <option key={m} value={m}>{t(`enum.${m}`)}</option>)}
        </select>
      </div>
    </>
  );
}

const ACTION_ICON: Record<string, string> = { open: "up", close: "down", stop: "stop", lock: "lock", unlock: "unlock" };

function ButtonsCtl({ cap, view, send, disabled, pending, actions }: CtlProps & { actions: string[] }) {
  const { t } = useTranslation();
  const confirmAttr = CAPABILITIES[cap].confirm_attribute;
  return (
    <>
      {Object.keys(view.attributes).map((a) => (
        <ValueView key={a} attr={a} label={attrLabel(t, a)} value={view.attributes[a]}
          pending={pending && a === confirmAttr} big={a === confirmAttr} />
      ))}
      {cap === "contactor" && <p className="muted" style={{ margin: 0 }}>{t("control.auxNote")}</p>}
      {cap === "breaker" && view.attributes.tripped?.value === true &&
        <p className="error" role="alert" style={{ margin: 0 }}>{t("panel.trippedHint")}</p>}
      <div className="seg">
        {actions.map((a, i) => (
          <button key={a} className={i === 0 ? "primary" : ""} disabled={disabled}
            onClick={() => send(cap, a)}><Icon name={cap === "contactor" || cap === "breaker" ? "power" : ACTION_ICON[a] ?? "power"} size={18} /> {actionLabel(t, cap, a)}</button>
        ))}
      </div>
    </>
  );
}

function ValveCtl({ cap, view, send, disabled, pending }: CtlProps) {
  const { t } = useTranslation();
  const maxRuntime = Number(view.config.max_runtime_s ?? CAPABILITIES.valve.actions.open.params.properties?.duration_s?.maximum ?? 3600);
  const maxMin = Math.floor(maxRuntime / 60);
  const [minutes, setMinutes] = useState("");
  const m = Number(minutes);
  const valid = minutes !== "" && Number.isInteger(m) && m >= 1 && m <= maxMin;
  return (
    <>
      <ValueView attr="open" label={attrLabel(t, "open")} value={view.attributes.open} pending={pending} big />
      <ValueView attr="flow" label={attrLabel(t, "flow")} value={view.attributes.flow} />
      <ValueView attr="remaining_s" label={attrLabel(t, "remaining_s")} value={view.attributes.remaining_s} />
      <label>{t("control.durationMin")}
        <input type="number" inputMode="numeric" min={1} max={maxMin} value={minutes}
          onChange={(e) => setMinutes(e.target.value)} disabled={disabled} />
        <span className="muted">{t("control.maxRuntime", { max: maxMin })}</span>
      </label>
      <div className="row">
        <button className="primary" disabled={disabled || !valid}
          title={valid ? undefined : t("control.durationRequired")}
          onClick={() => send(cap, "open", { duration_s: m * 60 })}><Icon name="drop" size={18} /> {t("action.open")}</button>
        <button disabled={disabled} onClick={() => send(cap, "close")}><Icon name="stop" size={18} /> {t("action.close")}</button>
      </div>
    </>
  );
}

/** Security system on the hub (ADR 0012). Every action is high risk -> PIN. */
function AlarmCtl({ cap, view, send, disabled, pending }: CtlProps) {
  const { t } = useTranslation();
  const { home } = useCurrentHome();
  const devices = useDevices(home?.id, true);
  const st = view.attributes.state;
  const known = !!st && (st.quality === "good" || st.quality === "stale") && typeof st.value === "string";
  const state = known ? String(st!.value) : "unknown";
  const zoneKey = typeof view.attributes.alert_zone?.value === "string" ? String(view.attributes.alert_zone.value) : "";
  const zone = zoneKey && ((devices.data ?? []).find((d) => d.key === zoneKey)?.name ?? zoneKey);
  return (
    <>
      <div className="alarm-ring" data-state={state} data-pending={pending} data-testid="alarm-state">
        <span className="ring"><Icon name={state === "disarmed" ? "unlock" : "shield"} size={38} /></span>
        <strong>{formatValue(st, t, "alarm_state")}</strong>
        {zone && ["pending", "triggered"].includes(state) && <span className="zone">{t("alarm.zone", { zone })}</span>}
      </div>
      <ValueView attr="alarm_state" label={attrLabel(t, "state")} value={st} pending={pending} />
      <div className="seg alarm-actions">
        <button className={state === "armed_away" ? "primary" : ""} disabled={disabled} onClick={() => send(cap, "arm_away")}>
          <Icon name="lock" size={18} /> {t("action.arm_away")}</button>
        <button className={state === "armed_home" ? "primary" : ""} disabled={disabled} onClick={() => send(cap, "arm_home")}>
          <Icon name="home" size={18} /> {t("action.arm_home")}</button>
        <button className={state !== "disarmed" && state !== "unknown" ? "danger" : ""} disabled={disabled} onClick={() => send(cap, "disarm")}>
          <Icon name="unlock" size={18} /> {t("action.disarm")}</button>
      </div>
    </>
  );
}

function MediaCtl({ cap, view, send, disabled, pending }: CtlProps) {
  const { t } = useTranslation();
  return (
    <>
      <div className="sw-line">
        <ValueView attr="on" label={attrLabel(t, "on")} value={view.attributes.on} pending={pending} big />
        <PowerSwitch on={reportedBool(view.attributes.on)} label={t("cap.media")} pending={pending} disabled={disabled}
          onTurnOn={() => send(cap, "turn_on")} onTurnOff={() => send(cap, "turn_off")} />
      </div>
      <MediaControl view={view} send={send} disabled={disabled} />
    </>
  );
}

function ReadOnlyCtl({ view }: CtlProps) {
  const { t } = useTranslation();
  return <>{Object.keys(view.attributes).map((a) => <ValueView key={a} attr={a} label={attrLabel(t, a)} value={view.attributes[a]} />)}</>;
}

const CONTROLS: Record<string, (p: CtlProps) => JSX.Element> = {
  switch: SwitchCtl,
  dimmer: DimmerCtl,
  climate: ClimateCtl,
  valve: ValveCtl,
  cover: (p) => <ButtonsCtl {...p} actions={["open", "stop", "close"]} />,
  lock: (p) => <ButtonsCtl {...p} actions={["unlock", "lock"]} />,
  contactor: (p) => <ButtonsCtl {...p} actions={["close", "open"]} />,
  breaker: (p) => <ButtonsCtl {...p} actions={["close", "open"]} />,
  alarm: AlarmCtl,
  remote: ({ view, send, disabled, pending }) => <RemoteControl view={view} send={send} disabled={disabled} pending={pending} />,
  media: MediaCtl,
};

/**
 * Sending from any control surface (detail page, tile): high-risk actions ask for the PIN first;
 * `pendingFor(cap)` is true while that capability's command is in flight.
 */
export function useDeviceSend(device: Device) {
  const { t } = useTranslation();
  const me = useSession((s) => s.me);
  const { send, tracked, busy } = useCommand(device.id);
  const [pinFor, setPinFor] = useState<{ cap: string; action: string; params?: Record<string, unknown> } | null>(null);
  const doSend: Send = (cap, action, params) => {
    if (CAPABILITIES[cap]?.risk === "high") { setPinFor({ cap, action, params }); return; }
    void send(cap, action, params).catch(() => undefined);
  };
  const pendingFor = (cap: string) => !!tracked && tracked.capability === cap &&
    (["sending", "queued", "sent"].includes(tracked.status) || (tracked.status === "acked" && hasFeedback(cap, tracked.action)));
  const pinUi = (
    <>
      {pinFor && !me?.has_pin && <p className="error">{t("control.noPin")}</p>}
      <PinDialog open={!!pinFor && !!me?.has_pin} action={pinFor ? actionLabel(t, pinFor.cap, pinFor.action) : ""}
        onCancel={() => setPinFor(null)}
        onSubmit={(pin) => { const p = pinFor!; setPinFor(null); void send(p.cap, p.action, p.params, pin).catch(() => undefined); }} />
    </>
  );
  return { doSend, tracked, busy, pendingFor, pinUi };
}

export function DeviceControls({ device, role, compact = false }: { device: Device; role?: Role; compact?: boolean }) {
  const { t } = useTranslation();
  const { doSend, tracked, busy, pendingFor, pinUi } = useDeviceSend(device);
  const caps = Object.keys(device.capabilities);
  const offline = !device.hub_online || device.availability.status === "offline" || !device.enabled;

  return (
    <div style={{ display: "grid", gap: 10 }}>
      {caps.map((cap) => {
        const view = device.capabilities[cap];
        const Ctl = CONTROLS[cap] ?? ReadOnlyCtl;
        const allowed = can(role, view.permission);
        const isControl = Object.keys(CAPABILITIES[cap]?.actions ?? {}).length > 0;
        return (
          <section key={cap} aria-label={t(`cap.${cap}`)} style={{ display: "grid", gap: 8 }}>
            {!compact && caps.length > 1 && <strong>{t(`cap.${cap}`)}</strong>}
            <Ctl device={device} cap={cap} view={view} send={doSend}
              disabled={!allowed || busy || offline} pending={pendingFor(cap)} />
            {isControl && !allowed && <span className="muted">{t("control.readOnly")}</span>}
          </section>
        );
      })}
      <CommandStatus tracked={tracked} />
      {pinUi}
    </div>
  );
}
