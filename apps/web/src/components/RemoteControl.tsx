/**
 * IR remote (ADR 0016): a TV or air-conditioner remote drawn in the app. Buttons are taught
 * from the original remote: in "learn" mode a tap asks the hub to listen, the owner presses
 * the same button on the old remote, and the button becomes usable only when the hub REALLY
 * captured the code (it shows up in `buttons`). A press is only "sent": IR has no feedback,
 * so the app never claims the TV or AC actually reacted.
 */
import { useState } from "react";
import { useTranslation } from "react-i18next";
import type { CapabilityView } from "../api/types";
import { Icon } from "./Icon";

type Send = (cap: string, action: string, params?: Record<string, unknown>) => void;

const TV: (string | null)[][] = [
  ["power", "input", "mute"],
  ["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"], [null, "0", null],
  ["vol_up", "up", "ch_up"],
  ["left", "ok", "right"],
  ["vol_down", "down", "ch_down"],
  ["back", "home", "menu"],
];
const AC: (string | null)[][] = [
  ["on", "off"],
  ["cool_18", "cool_22", "cool_24"],
  ["heat_26", "fan", "dry"],
  ["swing", "turbo", "sleep"],
];
const ICONS: Record<string, string> = {
  power: "power", on: "power", off: "stop", up: "up", down: "down", left: "back", right: "chevron",
  vol_up: "plus", vol_down: "minus", mute: "speaker", home: "home",
  back: "back", menu: "more", input: "tv", fan: "fan", dry: "drop", heat_26: "sun",
};
const id = (b: string) => (/^\d$/.test(b) ? `num_${b}` : b);

export function RemoteControl({ view, send, disabled, pending }: {
  view: CapabilityView; send: Send; disabled: boolean; pending: boolean;
}) {
  const { t } = useTranslation();
  const [learning, setLearning] = useState(false);
  const [waitingFor, setWaitingFor] = useState<string | null>(null);
  const [custom, setCustom] = useState("");
  const b = view.attributes.buttons;
  const known = !!b && (b.quality === "good" || b.quality === "stale") && Array.isArray(b.value);
  const learned = new Set(known ? (b!.value as string[]) : []);
  const layout = (view.config?.layout as string) || "other";
  const grid = layout === "tv" ? TV : layout === "ac" ? AC : [];
  const inLayout = new Set(grid.flat().filter(Boolean).map((x) => id(x!)));
  const extra = [...learned].filter((x) => !inLayout.has(x)).sort();
  const label = (x: string) => t(`remote.btn.${x}`, { defaultValue: x.replace(/^num_/, "").replace(/_/g, " ") });

  const tap = (button: string) => {
    if (learning) { setWaitingFor(button); send("remote", "learn", { button }); return; }
    if (learned.has(button)) send("remote", "press", { button });
  };
  const Btn = ({ name }: { name: string }) => {
    const has = learned.has(name);
    return (
      <button type="button" className={`rbtn ${has ? "has" : "missing"} ${waitingFor === name && pending ? "listening" : ""}`}
        disabled={disabled || (!learning && !has)} aria-label={label(name)} title={has ? label(name) : t("remote.notLearned")}
        onClick={() => tap(name)} data-testid={`rbtn-${name}`}>
        {ICONS[name] ? <Icon name={ICONS[name]} size={20} /> : <span>{label(name)}</span>}
      </button>
    );
  };
  const customOk = /^[a-z0-9_]{1,32}$/.test(custom);

  return (
    <div className={`remote layout-${layout}`}>
      <div className="row spread">
        <span className="muted">{known ? t("remote.learnedCount", { count: learned.size }) : t("status.unknown")}</span>
        <button type="button" className={learning ? "primary small" : "small"} aria-pressed={learning}
          disabled={disabled} onClick={() => { setLearning(!learning); setWaitingFor(null); }}>
          <Icon name="edit" size={16} /> {learning ? t("remote.learnDone") : t("remote.learnMode")}
        </button>
      </div>
      {learning && (
        <p className="note" role="status">
          <Icon name="send" size={18} />
          {waitingFor && pending ? t("remote.listening", { button: label(waitingFor) }) : t("remote.learnHint")}
        </p>
      )}
      {grid.map((row, i) => (
        <div key={i} className="rrow" style={{ gridTemplateColumns: `repeat(${row.length}, 1fr)` }}>
          {row.map((x, j) => (x ? <Btn key={x} name={id(x)} /> : <span key={j} />))}
        </div>
      ))}
      {extra.length > 0 && (
        <div className="rrow" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
          {extra.map((x) => <Btn key={x} name={x} />)}
        </div>
      )}
      {learning && (
        <div className="row">
          <input value={custom} maxLength={32} placeholder={t("remote.customPh")} aria-label={t("remote.custom")}
            onChange={(e) => setCustom(e.target.value.toLowerCase().replace(/[^a-z0-9_]/g, "_"))} style={{ flex: 1 }} />
          <button type="button" disabled={disabled || !customOk} onClick={() => { tap(custom); setCustom(""); }}>
            <Icon name="plus" size={16} /> {t("remote.custom")}
          </button>
        </div>
      )}
      <p className="muted" style={{ margin: 0 }}>{t("remote.noFeedback")}</p>
    </div>
  );
}

/** TV through Yandex Alisa (ADR 0016): power, volume, channel; the cloud reports the state. */
export function MediaControl({ view, send, disabled }: {
  view: CapabilityView; send: Send; disabled: boolean;
}) {
  const { t } = useTranslation();
  const a = view.attributes;
  const num = (k: string) => (a[k] && (a[k].quality === "good" || a[k].quality === "stale") && typeof a[k].value === "number" ? (a[k].value as number) : null);
  const vol = num("volume");
  const ch = num("channel");
  return (
    <div className="remote">
      <div className="rrow" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
        <button type="button" className="rbtn has" disabled={disabled} aria-label={t("action.volume_down")} onClick={() => send("media", "volume_down")}><Icon name="minus" size={20} /></button>
        <span className="rval">{t("attr.volume")}<strong>{vol ?? "—"}</strong></span>
        <button type="button" className="rbtn has" disabled={disabled} aria-label={t("action.volume_up")} onClick={() => send("media", "volume_up")}><Icon name="plus" size={20} /></button>
        <button type="button" className="rbtn has" disabled={disabled} aria-label={t("action.channel_down")} onClick={() => send("media", "channel_down")}><Icon name="down" size={20} /></button>
        <span className="rval">{t("attr.channel")}<strong>{ch ?? "—"}</strong></span>
        <button type="button" className="rbtn has" disabled={disabled} aria-label={t("action.channel_up")} onClick={() => send("media", "channel_up")}><Icon name="up" size={20} /></button>
      </div>
      <button type="button" disabled={disabled} onClick={() => send("media", "set_mute", { muted: a.muted?.value !== true })}>
        <Icon name="speaker" size={18} /> {t("action.set_mute")}
      </button>
    </div>
  );
}
