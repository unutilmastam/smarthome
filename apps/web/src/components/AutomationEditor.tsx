import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../api/client";
import type { AutoAction, Automation, AutomationDef, Condition, Device, Home, Trigger } from "../api/types";
import { automatable, DAYS, defaultValue, valueLabel, watchable } from "../lib/automation";
import { CAPABILITIES, type AttrSpec } from "../lib/contracts";
import { errorText } from "./CommandStatus";
import { Icon } from "./Icon";
import { Sheet } from "./Sheet";

const NEW: AutomationDef = { triggers: [], conditions: [], actions: [], cooldown_s: 60, max_runs_per_hour: 20, manual_override_s: 1800 };

/** Value input driven by the attribute schema from the contract (never free text for enums). */
function ValueInput({ attr, spec, value, onChange, label }: {
  attr: string; spec?: AttrSpec; value: unknown; onChange: (v: unknown) => void; label: string;
}) {
  const { t } = useTranslation();
  if (!spec || spec.type === "boolean") {
    return (
      <select aria-label={label} value={String(value)} onChange={(e) => onChange(e.target.value === "true")}>
        <option value="true">{valueLabel(t, attr, spec, true)}</option>
        <option value="false">{valueLabel(t, attr, spec, false)}</option>
      </select>
    );
  }
  if (spec.enum) {
    return (
      <select aria-label={label} value={String(value)} onChange={(e) => onChange(e.target.value)}>
        {spec.enum.map((v) => <option key={v} value={v}>{valueLabel(t, attr, spec, v)}</option>)}
      </select>
    );
  }
  return (
    <input aria-label={label} type="number" value={Number(value)} min={spec.minimum} max={spec.maximum}
      step={spec.type === "integer" ? 1 : 0.5} onChange={(e) => onChange(Number(e.target.value))} />
  );
}

/** device -> watchable attribute -> value. */
function StatePicker({ devices, device, capability, attribute, value, onChange, valueLabelText }: {
  devices: Device[]; device: string; capability: string; attribute: string; value: unknown;
  onChange: (p: { device: string; capability: string; attribute: string; value: unknown }) => void;
  valueLabelText: string;
}) {
  const { t } = useTranslation();
  const usable = devices.filter((d) => watchable(d).length);
  const d = devices.find((x) => x.key === device);
  const opts = d ? watchable(d) : [];
  const spec = CAPABILITIES[capability]?.attributes[attribute];
  const pickDevice = (key: string) => {
    const nd = devices.find((x) => x.key === key);
    const first = nd ? watchable(nd)[0] : undefined;
    onChange({ device: key, capability: first?.cap ?? "", attribute: first?.attr ?? "", value: defaultValue(first?.spec) });
  };
  return (
    <div className="rule-fields">
      <select aria-label={t("auto.device")} value={device} onChange={(e) => pickDevice(e.target.value)}>
        <option value="" disabled>{t("auto.device")}</option>
        {usable.map((x) => <option key={x.key} value={x.key}>{x.name}</option>)}
      </select>
      {d && (
        <select aria-label={t("auto.attribute")} value={`${capability}.${attribute}`}
          onChange={(e) => {
            const [cap, attr] = e.target.value.split(".");
            onChange({ device, capability: cap, attribute: attr, value: defaultValue(CAPABILITIES[cap]?.attributes[attr]) });
          }}>
          {opts.map((o) => <option key={`${o.cap}.${o.attr}`} value={`${o.cap}.${o.attr}`}>{t(`cap.${o.cap}`)} · {t(`attr.${o.attr}`)}</option>)}
        </select>
      )}
      {d && attribute && (
        <ValueInput attr={attribute} spec={spec} value={value} label={valueLabelText}
          onChange={(v) => onChange({ device, capability, attribute, value: v })} />
      )}
    </div>
  );
}

function Days({ value, onChange }: { value?: string[]; onChange: (v?: string[]) => void }) {
  const { t } = useTranslation();
  const set = new Set(value ?? DAYS);
  return (
    <div className="chips wrap days" role="group" aria-label={t("auto.days")}>
      {DAYS.map((d) => (
        <button key={d} type="button" aria-pressed={set.has(d)} onClick={() => {
          const n = new Set(set);
          if (n.has(d)) n.delete(d); else n.add(d);
          onChange(n.size === 7 || n.size === 0 ? undefined : DAYS.filter((x) => n.has(x)));
        }}>{t(`day.${d}`)}</button>
      ))}
    </div>
  );
}

function Row({ icon, title, onRemove, children }: { icon: string; title: string; onRemove: () => void; children: React.ReactNode }) {
  const { t } = useTranslation();
  return (
    <div className="rule-row">
      <div className="rule-row-head">
        <span className="ico"><Icon name={icon} size={18} /></span>
        <strong>{title}</strong>
        <button type="button" className="icon-btn" aria-label={`${t("app.delete")}: ${title}`} onClick={onRemove}>
          <Icon name="close" size={16} />
        </button>
      </div>
      {children}
    </div>
  );
}

function TriggerEditor({ tr, devices, onChange }: { tr: Trigger; devices: Device[]; onChange: (t: Trigger) => void }) {
  const { t } = useTranslation();
  if (tr.type === "state") {
    return (
      <StatePicker devices={devices} device={tr.device} capability={tr.capability} attribute={tr.attribute}
        value={tr.to} valueLabelText={t("auto.becomes")}
        onChange={(p) => onChange({ ...tr, device: p.device, capability: p.capability, attribute: p.attribute, to: p.value })} />
    );
  }
  if (tr.type === "time") {
    return (
      <div className="rule-fields">
        <input type="time" aria-label={t("auto.time")} value={tr.at} required onChange={(e) => onChange({ ...tr, at: e.target.value })} />
        <Days value={tr.days} onChange={(days) => onChange({ ...tr, days })} />
      </div>
    );
  }
  return (
    <div className="rule-fields">
      <select aria-label={t("auto.sunEvent")} value={tr.event} onChange={(e) => onChange({ ...tr, event: e.target.value as "sunrise" | "sunset" })}>
        <option value="sunset">{t("auto.sunset")}</option>
        <option value="sunrise">{t("auto.sunrise")}</option>
      </select>
      <label className="inline">{t("auto.offset")}
        <input type="number" min={-180} max={180} value={tr.offset_min ?? 0} onChange={(e) => onChange({ ...tr, offset_min: Number(e.target.value) })} />
      </label>
    </div>
  );
}

function ConditionEditor({ c, devices, onChange }: { c: Condition; devices: Device[]; onChange: (c: Condition) => void }) {
  const { t } = useTranslation();
  if (c.type === "state") {
    return (
      <StatePicker devices={devices} device={c.device} capability={c.capability} attribute={c.attribute}
        value={c.is} valueLabelText={t("auto.is")}
        onChange={(p) => onChange({ ...c, device: p.device, capability: p.capability, attribute: p.attribute, is: p.value })} />
    );
  }
  if (c.type === "time") {
    return (
      <div className="rule-fields">
        <input type="time" aria-label={t("auto.after")} value={c.after} onChange={(e) => onChange({ ...c, after: e.target.value })} />
        <input type="time" aria-label={t("auto.before")} value={c.before} onChange={(e) => onChange({ ...c, before: e.target.value })} />
      </div>
    );
  }
  if (c.type === "sun") {
    return (
      <div className="seg" role="radiogroup" aria-label={t("auto.dayNight")}>
        {(["night", "day"] as const).map((v) => (
          <button key={v} type="button" role="radio" aria-checked={c.is === v} className={c.is === v ? "primary" : ""}
            onClick={() => onChange({ ...c, is: v })}><Icon name={v === "night" ? "moon" : "sun"} size={16} /> {t(`auto.${v}`)}</button>
        ))}
      </div>
    );
  }
  const modes = ["disarmed", "armed_away", "armed_home", "triggered"];
  return (
    <div className="chips wrap" role="group" aria-label={t("auto.securityMode")}>
      {modes.map((m) => (
        <button key={m} type="button" aria-pressed={c.is.includes(m)} onClick={() => {
          const next = c.is.includes(m) ? c.is.filter((x) => x !== m) : [...c.is, m];
          onChange({ ...c, is: next.length ? next : c.is });
        }}>{t(`enum.${m}`)}</button>
      ))}
    </div>
  );
}

function ActionEditor({ a, devices, onChange }: { a: AutoAction; devices: Device[]; onChange: (a: AutoAction) => void }) {
  const { t } = useTranslation();
  if (a.type === "delay") {
    return (
      <label className="inline">{t("auto.seconds")}
        <input type="number" min={1} max={3600} value={a.seconds} onChange={(e) => onChange({ ...a, seconds: Number(e.target.value) })} />
      </label>
    );
  }
  if (a.type === "notify") {
    return (
      <div className="rule-fields">
        <input aria-label={t("auto.text")} maxLength={200} required value={a.text} placeholder={t("auto.textHint")}
          onChange={(e) => onChange({ ...a, text: e.target.value })} />
        <select aria-label={t("events.filter")} value={a.severity ?? "info"} onChange={(e) => onChange({ ...a, severity: e.target.value as "info" })}>
          {(["info", "warning", "critical"] as const).map((s) => <option key={s} value={s}>{t(`severity.${s}`)}</option>)}
        </select>
      </div>
    );
  }
  const usable = devices.filter((d) => automatable(d).length);
  const d = devices.find((x) => x.key === a.device);
  const acts = d ? automatable(d) : [];
  const props = CAPABILITIES[a.capability]?.actions[a.action]?.params.properties ?? {};
  const required = CAPABILITIES[a.capability]?.actions[a.action]?.params.required ?? [];
  const defaults = (cap: string, action: string) => {
    const p: Record<string, unknown> = {};
    const spec = CAPABILITIES[cap]?.actions[action]?.params;
    for (const k of spec?.required ?? []) p[k] = defaultValue(spec?.properties?.[k]);
    return p;
  };
  return (
    <div className="rule-fields">
      <select aria-label={t("auto.device")} value={a.device} onChange={(e) => {
        const nd = devices.find((x) => x.key === e.target.value);
        const first = nd ? automatable(nd)[0] : undefined;
        onChange({ type: "command", device: e.target.value, capability: first?.cap ?? "", action: first?.action ?? "",
          params: first ? defaults(first.cap, first.action) : {} });
      }}>
        <option value="" disabled>{t("auto.device")}</option>
        {usable.map((x) => <option key={x.key} value={x.key}>{x.name}</option>)}
      </select>
      {d && (
        <select aria-label={t("auto.action")} value={`${a.capability}.${a.action}`} onChange={(e) => {
          const [cap, action] = e.target.value.split(".");
          onChange({ type: "command", device: a.device, capability: cap, action, params: defaults(cap, action) });
        }}>
          {acts.map((o) => <option key={`${o.cap}.${o.action}`} value={`${o.cap}.${o.action}`}>{t(`cap.${o.cap}`)}: {t(`action.${o.action}`)}</option>)}
        </select>
      )}
      {Object.entries(props).filter(([k]) => required.includes(k)).map(([k, spec]) => (
        <label key={k} className="inline">{t(`param.${k}`, { defaultValue: k })}
          <ValueInput attr={k} spec={spec} label={t(`param.${k}`, { defaultValue: k })} value={a.params?.[k]}
            onChange={(v) => onChange({ ...a, params: { ...(a.params ?? {}), [k]: v } })} />
        </label>
      ))}
      {a.capability === "switch" && a.action === "turn_on" && (
        <label className="inline">{t("auto.autoOff")}
          <input type="number" min={0} max={1440} value={a.auto_off_after_s ? Math.round(a.auto_off_after_s / 60) : 0}
            onChange={(e) => {
              const m = Number(e.target.value);
              const { auto_off_after_s: _drop, ...rest } = a;
              onChange(m > 0 ? { ...rest, auto_off_after_s: m * 60 } : rest);
            }} />
        </label>
      )}
      <p className="muted" style={{ margin: 0 }}>{t("auto.highRiskNote")}</p>
    </div>
  );
}

export function AutomationEditor({ open, onClose, home, devices, automation }: {
  open: boolean; onClose: () => void; home: Home; devices: Device[]; automation?: Automation;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [def, setDef] = useState<AutomationDef>(NEW);
  const [err, setErr] = useState<string[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [confirmDel, setConfirmDel] = useState(false);
  useEffect(() => {
    if (!open) return;
    setName(automation?.name ?? "");
    setDef(automation ? { conditions: [], ...automation.definition } : { ...NEW, triggers: [], conditions: [], actions: [] });
    setErr(null); setConfirmDel(false);
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  const firstKey = (pred: (d: Device) => boolean) => devices.find(pred)?.key ?? "";
  const stateDefaults = () => {
    const d = devices.find((x) => watchable(x).length);
    const w = d ? watchable(d)[0] : undefined;
    return { device: d?.key ?? "", capability: w?.cap ?? "", attribute: w?.attr ?? "", value: defaultValue(w?.spec) };
  };
  const addTrigger = (type: Trigger["type"]) => {
    const s = stateDefaults();
    const tr: Trigger = type === "state" ? { type, device: s.device, capability: s.capability, attribute: s.attribute, to: s.value }
      : type === "time" ? { type, at: "19:00" } : { type, event: "sunset", offset_min: 0 };
    setDef({ ...def, triggers: [...def.triggers, tr] });
  };
  const addCondition = (type: Condition["type"]) => {
    const s = stateDefaults();
    const c: Condition = type === "state" ? { type, device: s.device, capability: s.capability, attribute: s.attribute, is: s.value }
      : type === "time" ? { type, after: "22:00", before: "06:00" } : type === "sun" ? { type, is: "night" }
      : { type, is: ["armed_away"] };
    setDef({ ...def, conditions: [...(def.conditions ?? []), c] });
  };
  const addAction = (type: AutoAction["type"]) => {
    let a: AutoAction;
    if (type === "command") {
      const key = firstKey((d) => automatable(d).length > 0);
      const d = devices.find((x) => x.key === key);
      const first = d ? automatable(d)[0] : undefined;
      a = { type, device: key, capability: first?.cap ?? "", action: first?.action ?? "", params: {} };
    } else if (type === "delay") a = { type, seconds: 30 };
    else a = { type, text: "", severity: "info" };
    setDef({ ...def, actions: [...def.actions, a] });
  };
  const upd = <K extends "triggers" | "conditions" | "actions">(k: K, i: number, v: NonNullable<AutomationDef[K]>[number] | null) => {
    const list = [...((def[k] ?? []) as unknown[])];
    if (v === null) list.splice(i, 1); else list[i] = v;
    setDef({ ...def, [k]: list });
  };
  const needsCoords = [...def.triggers, ...(def.conditions ?? [])].some((x) => x.type === "sun")
    && (home.latitude === null || home.longitude === null);
  const hasAlarm = devices.some((d) => "alarm" in d.capabilities);

  const save = async () => {
    setErr(null); setBusy(true);
    const definition = { ...def, conditions: def.conditions?.length ? def.conditions : undefined };
    try {
      if (automation) await api.patch(`/automations/${automation.id}`, { name: name.trim(), definition });
      else await api.post(`/homes/${home.id}/automations`, { name: name.trim(), definition });
      void qc.invalidateQueries({ queryKey: ["automations", home.id] });
      onClose();
    } catch (e) {
      if (e instanceof ApiError) {
        const details = Array.isArray(e.details) ? (e.details as unknown[]).map((x) => (typeof x === "string" ? x : JSON.stringify(x))) : [];
        setErr([errorText(t, e.code, e.message), ...details]);
      } else setErr([t("errors.generic")]);
    } finally { setBusy(false); }
  };
  const remove = async () => {
    if (!automation) return;
    setBusy(true);
    try { await api.del(`/automations/${automation.id}`); void qc.invalidateQueries({ queryKey: ["automations", home.id] }); onClose(); }
    catch { setErr([t("errors.generic")]); } finally { setBusy(false); }
  };
  const valid = !!name.trim() && def.triggers.length > 0 && def.actions.length > 0 && !needsCoords;

  return (
    <Sheet open={open} onClose={onClose} title={automation ? t("auto.edit") : t("auto.new")}>
      <form className="form" onSubmit={(e) => { e.preventDefault(); if (valid) void save(); }}>
        <label>{t("auto.name")}<input required maxLength={120} value={name} onChange={(e) => setName(e.target.value)} placeholder={t("auto.namePh")} /></label>

        <fieldset className="pick rule-block">
          <legend><Icon name="play" size={16} /> {t("auto.when")}</legend>
          {def.triggers.map((tr, i) => (
            <Row key={i} icon={tr.type === "time" ? "clock" : tr.type === "sun" ? "moon" : "motion"} title={t(`auto.trigger.${tr.type}`)}
              onRemove={() => upd("triggers", i, null)}>
              <TriggerEditor tr={tr} devices={devices} onChange={(v) => upd("triggers", i, v)} />
            </Row>
          ))}
          <div className="chips wrap">
            {(["state", "time", "sun"] as const).map((x) => (
              <button key={x} type="button" className="ghost" onClick={() => addTrigger(x)}><Icon name="plus" size={14} /> {t(`auto.trigger.${x}`)}</button>
            ))}
          </div>
        </fieldset>

        <fieldset className="pick rule-block">
          <legend><Icon name="shield" size={16} /> {t("auto.if")}</legend>
          {(def.conditions ?? []).map((c, i) => (
            <Row key={i} icon={c.type === "time" ? "clock" : c.type === "sun" ? "sun" : c.type === "security_mode" ? "shield" : "devices"}
              title={t(`auto.cond.${c.type}`)} onRemove={() => upd("conditions", i, null)}>
              <ConditionEditor c={c} devices={devices} onChange={(v) => upd("conditions", i, v)} />
            </Row>
          ))}
          <div className="chips wrap">
            {(["state", "time", "sun", ...(hasAlarm ? ["security_mode"] : [])] as Condition["type"][]).map((x) => (
              <button key={x} type="button" className="ghost" onClick={() => addCondition(x)}><Icon name="plus" size={14} /> {t(`auto.cond.${x}`)}</button>
            ))}
          </div>
        </fieldset>

        <fieldset className="pick rule-block">
          <legend><Icon name="power" size={16} /> {t("auto.then")}</legend>
          {def.actions.map((a, i) => (
            <Row key={i} icon={a.type === "command" ? "power" : a.type === "delay" ? "clock" : "bell"} title={t(`auto.act.${a.type}`)}
              onRemove={() => upd("actions", i, null)}>
              <ActionEditor a={a} devices={devices} onChange={(v) => upd("actions", i, v)} />
            </Row>
          ))}
          <div className="chips wrap">
            {(["command", "delay", "notify"] as const).map((x) => (
              <button key={x} type="button" className="ghost" onClick={() => addAction(x)}><Icon name="plus" size={14} /> {t(`auto.act.${x}`)}</button>
            ))}
          </div>
        </fieldset>

        <details className="rule-advanced">
          <summary>{t("auto.advanced")}</summary>
          <div className="grid">
            <label>{t("auto.cooldown")}<input type="number" min={0} max={86400} value={def.cooldown_s ?? 60} onChange={(e) => setDef({ ...def, cooldown_s: Number(e.target.value) })} /></label>
            <label>{t("auto.maxPerHour")}<input type="number" min={1} max={120} value={def.max_runs_per_hour ?? 20} onChange={(e) => setDef({ ...def, max_runs_per_hour: Number(e.target.value) })} /></label>
            <label>{t("auto.override")}<input type="number" min={0} max={1440} value={Math.round((def.manual_override_s ?? 1800) / 60)} onChange={(e) => setDef({ ...def, manual_override_s: Number(e.target.value) * 60 })} /></label>
          </div>
        </details>

        <p className="note"><Icon name="hub" size={18} /> {t("auto.onHub")}</p>
        {needsCoords && <p className="error" role="alert">{t("auto.needCoords")}</p>}
        {err && <div className="error" role="alert">{err.map((x, i) => <div key={i}>{x}</div>)}</div>}
        <button className="primary block" type="submit" disabled={busy || !valid}>{t("app.save")}</button>
        {automation && (
          <div className="danger-zone">
            {!confirmDel ? (
              <button type="button" className="danger" onClick={() => setConfirmDel(true)}><Icon name="trash" size={18} /> {t("auto.remove")}</button>
            ) : (
              <div className="row">
                <button type="button" onClick={() => setConfirmDel(false)}>{t("app.cancel")}</button>
                <button type="button" className="danger" disabled={busy} onClick={() => void remove()}><Icon name="trash" size={18} /> {t("auto.removeYes")}</button>
              </div>
            )}
          </div>
        )}
      </form>
    </Sheet>
  );
}
