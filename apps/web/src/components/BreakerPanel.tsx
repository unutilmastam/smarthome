/**
 * Electrical panel (ADR 0015): smart breakers lined up on DIN rails by the number on their
 * label, like the real panel. The lever follows the REPORTED state only (`closed` from the
 * breaker's own contact); unknown = lever in the middle, never a guess. Every switch is a
 * high-risk command: PIN first. A tripped breaker cannot be switched on from the app.
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { Device, Role } from "../api/types";
import { useSession } from "../auth/session";
import { useCommand } from "../lib/commands";
import { actionLabel, can } from "../lib/contracts";
import { type BreakerInfo, type LeverState, good, groupPanels, nextPosition } from "../lib/panel";
import { formatValue } from "../lib/status";
import { useAddFlow, useCanConfigure } from "./AddFlow";
import { Icon } from "./Icon";
import { PinDialog } from "./PinDialog";

function nameSize(name: string): string {
  const longest = Math.max(...name.split(/\s+/).map((w) => w.length));
  return longest >= 10 ? "xlong" : longest > 8 ? "long" : "";
}

function Breaker({ info, role }: { info: BreakerInfo; role?: Role }) {
  const { t } = useTranslation();
  const me = useSession((s) => s.me);
  const { send, tracked, busy } = useCommand(info.device.id);
  const [pinFor, setPinFor] = useState<"close" | "open" | null>(null);
  const d = info.device;
  const offline = !d.hub_online || d.availability.status === "offline" || !d.enabled;
  const allowed = can(role, "control_power");
  const pending = !!tracked && ["sending", "queued", "sent", "acked"].includes(tracked.status);
  const leverAction = info.state === "on" ? "open" : info.state === "off" ? "close" : null;
  const disabled = !allowed || offline || busy || leverAction === null;
  const num = info.position ?? "–";
  const title = info.state === "tripped" ? t("panel.trippedHint")
    : info.state === "unknown" ? t("panel.unknownHint")
    : leverAction ? `${num} — ${d.name}: ${actionLabel(t, "breaker", leverAction)}` : "";
  const done = tracked && ["confirmed", "rejected", "failed", "expired", "timeout", "error"].includes(tracked.status);

  return (
    <div className="mcb" data-state={info.state} data-offline={offline || undefined}
      style={{ gridColumn: `span ${info.poles}` }} data-testid={`breaker-${d.key}`}>
      <div className={`mcb-num ${info.duplicate ? "dup" : ""}`} title={info.duplicate ? t("panel.duplicate") : undefined}>
        {num}{info.duplicate && " !"}
      </div>
      <div className="mcb-body">
        <span className="mcb-rating">{info.rating ?? ""}</span>
        <button type="button" className="mcb-lever" role="switch"
          aria-checked={info.state === "on" ? true : info.state === "unknown" ? "mixed" : false}
          aria-label={`${num} — ${d.name}`} title={title} disabled={disabled} data-pending={pending || undefined}
          onClick={() => leverAction && setPinFor(leverAction)}>
          <span className="handle" aria-hidden="true">{info.state === "unknown" ? "?" : ""}</span>
        </button>
        <span className="mcb-window" aria-hidden="true" />
        <span className="mcb-io" aria-hidden="true">{info.state === "tripped" ? "TRIP" : "I · O"}</span>
      </div>
      {/* Narrow module: long single words ("Mehmonxona") get a smaller font instead of being cut. */}
      <Link to={`/devices/${d.id}`} className={`mcb-name ${nameSize(d.name)}`}>{d.name}</Link>
      <span className="mcb-sub">
        {info.state === "tripped" ? <strong className="error">{t("panel.tripped")}</strong>
          : offline ? t("availability.offline")
          : info.power && good(info.power) ? formatValue(info.power, t, "power")
          : t(`panel.state.${info.state}`)}
      </span>
      {done && tracked && (
        <span className={`mcb-cmd ${tracked.status === "confirmed" ? "ok" : "bad"}`} role="status">
          {t(`command.${tracked.status}`)}
        </span>
      )}
      {pinFor && !me?.has_pin && <span className="error mcb-cmd">{t("control.noPin")}</span>}
      <PinDialog open={!!pinFor && !!me?.has_pin} action={pinFor ? `${num} — ${d.name}: ${actionLabel(t, "breaker", pinFor)}` : ""}
        onCancel={() => setPinFor(null)}
        onSubmit={(pin) => { const a = pinFor!; setPinFor(null); void send("breaker", a, {}, pin).catch(() => undefined); }} />
    </div>
  );
}

export function BreakerPanels({ devices, role }: { devices: Device[]; role?: Role }) {
  const { t } = useTranslation();
  const canAdd = useCanConfigure();
  const openAdd = useAddFlow((s) => s.open);
  const panels = groupPanels(devices);
  if (panels.length === 0) {
    return (
      <div className="card din-empty">
        <Icon name="breaker" size={28} />
        <p className="muted" style={{ margin: 0 }}>{t("panel.empty")}</p>
        {canAdd && <button className="primary" onClick={() => openAdd("device", { preset: { type: "breaker" } })}>
          <Icon name="plus" size={18} /> {t("panel.add")}</button>}
      </div>
    );
  }
  return (
    <>
      {panels.map(({ panel, items }) => {
        const count = (s: LeverState) => items.filter((i) => i.state === s).length;
        return (
          <section key={panel || "_"} className="din-panel" aria-label={panel || t("panel.default")}>
            <header>
              <strong>{panel || t("panel.default")}</strong>
              <span className="muted">
                {t("panel.summary", { total: items.length, on: count("on"), off: count("off") })}
                {count("tripped") > 0 && <> · <span className="error">{t("panel.trippedCount", { count: count("tripped") })}</span></>}
                {count("unknown") > 0 && <> · {t("panel.unknownCount", { count: count("unknown") })}</>}
              </span>
            </header>
            <div className="din-rails">
              {items.map((i) => <Breaker key={i.device.id} info={i} role={role} />)}
              {canAdd && (
                <button type="button" className="mcb mcb-add" aria-label={t("panel.add")}
                  onClick={() => openAdd("device", { preset: { type: "breaker", panel, position: nextPosition(items) } })}>
                  <span className="mcb-num">{nextPosition(items)}</span>
                  <Icon name="plus" size={22} />
                </button>
              )}
            </div>
            {!can(role, "control_power") && <p className="muted din-note">{t("panel.readOnly")}</p>}
          </section>
        );
      })}
    </>
  );
}
