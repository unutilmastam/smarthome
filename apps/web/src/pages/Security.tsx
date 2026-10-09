import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../api/client";
import { useDevices, useEvents } from "../api/hooks";
import type { Device } from "../api/types";
import { useCanConfigure } from "../components/AddFlow";
import { errorText } from "../components/CommandStatus";
import { AvailabilityBadge, DeviceIcon, deviceClasses } from "../components/DeviceCard";
import { DeviceControls } from "../components/DeviceControls";
import { EventList } from "../components/EventFeed";
import { Icon } from "../components/Icon";
import { useLive } from "../components/Layout";
import { Sheet } from "../components/Sheet";
import { ValueView } from "../components/ValueView";
import { useCurrentHome } from "../lib/home";

interface Zone { device_key: string; capability: "contact" | "motion"; mode: "entry" | "instant"; home?: boolean }
interface AlarmConfig { zones: Zone[]; sirens: string[]; exit_delay_s: number; entry_delay_s: number; siren_max_s: number }

const DEFAULTS: AlarmConfig = { zones: [], sirens: [], exit_delay_s: 30, entry_delay_s: 30, siren_max_s: 180 };

/** The security system lives on the hub (ADR 0012); this page shows and configures it. */
export function Security() {
  const { t } = useTranslation();
  const { home } = useCurrentHome();
  const devices = useDevices(home?.id, useLive());
  const canEdit = useCanConfigure();
  const [setup, setSetup] = useState(false);
  const alarm = (devices.data ?? []).find((d) => "alarm" in d.capabilities);
  const events = useEvents(home?.id, { capability: "alarm", limit: 20 });
  if (devices.isLoading) return <p>{t("app.loading")}</p>;
  const all = devices.data ?? [];
  const cfg = (alarm?.capabilities.alarm.config ?? {}) as Partial<AlarmConfig>;
  const zones = (cfg.zones ?? []).map((z) => ({ z, d: all.find((d) => d.key === z.device_key) }));
  return (
    <>
      <div className="page-head">
        <h2>{t("security.title")}</h2>
        {alarm && canEdit && (
          <button className="ghost" onClick={() => setSetup(true)}><Icon name="settings" size={18} /> {t("security.configure")}</button>
        )}
      </div>
      {!alarm ? (
        <div className="empty card hero">
          <span className="ico big"><Icon name="shield" size={36} /></span>
          <h2>{t("security.none")}</h2>
          <p className="muted">{t("security.noneHint")}</p>
          {canEdit && <button className="primary" onClick={() => setSetup(true)}><Icon name="plus" size={18} /> {t("security.setup")}</button>}
        </div>
      ) : (
        <div className="security-grid">
          <article className={`${deviceClasses(alarm)} alarm-card`} data-testid={`device-${alarm.key}`}>
            <DeviceControls device={alarm} role={home?.my_role} compact />
            <p className="note"><Icon name="hub" size={18} /> {t("security.onHub")}</p>
          </article>
          <section className="card">
            <h3>{t("security.zones")}</h3>
            <ul className="zones">
              {zones.map(({ z, d }) => <ZoneRow key={z.device_key} zone={z} device={d} />)}
            </ul>
          </section>
          <section className="card">
            <h3>{t("security.recent")}</h3>
            <EventList events={events.data ?? []} />
          </section>
        </div>
      )}
      {canEdit && home && (
        <SecuritySetup open={setup} onClose={() => setSetup(false)} homeId={home.id} devices={all} alarm={alarm} />
      )}
    </>
  );
}

function ZoneRow({ zone, device }: { zone: Zone; device?: Device }) {
  const { t } = useTranslation();
  if (!device) return <li className="zone missing"><Icon name="alert" size={18} /> {zone.device_key} — {t("security.zoneMissing")}</li>;
  const v = device.capabilities[zone.capability]?.attributes[zone.capability === "contact" ? "open" : "detected"];
  return (
    <li className={`zone ${v?.value === true ? "zone-open" : ""}`}>
      <span className={deviceClasses(device).replace("card ", "")}><DeviceIcon device={device} size={20} /></span>
      <div className="zone-body">
        <strong>{device.name}</strong>
        <span className="muted">{t(`security.mode.${zone.mode}`)}{(zone.home ?? zone.capability === "contact") ? ` · ${t("security.alsoHome")}` : ""}</span>
      </div>
      <ValueView attr={zone.capability === "contact" ? "open" : "detected"} label="" value={v} />
      <AvailabilityBadge device={device} />
    </li>
  );
}

function SecuritySetup({ open, onClose, homeId, devices, alarm }: {
  open: boolean; onClose: () => void; homeId: string; devices: Device[]; alarm?: Device;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [cfg, setCfg] = useState<AlarmConfig>(DEFAULTS);
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (open) { setCfg({ ...DEFAULTS, ...(alarm?.capabilities.alarm.config as Partial<AlarmConfig> ?? {}) }); setErr(null); }
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps
  const sensors = devices.flatMap((d) => (["contact", "motion"] as const)
    .filter((c) => c in d.capabilities).map((c) => ({ d, c })));
  const switches = devices.filter((d) => "switch" in d.capabilities);
  const zoneOf = (key: string, c: string) => cfg.zones.find((z) => z.device_key === key && z.capability === c);
  const toggleZone = (key: string, c: "contact" | "motion") => setCfg({
    ...cfg, zones: zoneOf(key, c) ? cfg.zones.filter((z) => !(z.device_key === key && z.capability === c))
      : [...cfg.zones, { device_key: key, capability: c, mode: c === "contact" ? "entry" : "instant", home: c === "contact" }],
  });
  const patchZone = (key: string, c: string, p: Partial<Zone>) =>
    setCfg({ ...cfg, zones: cfg.zones.map((z) => (z.device_key === key && z.capability === c ? { ...z, ...p } : z)) });
  // The engine keys zones by device; one capability per device.
  const dupes = new Set(cfg.zones.map((z) => z.device_key)).size !== cfg.zones.length;
  const save = async () => {
    setErr(null); setBusy(true);
    const capabilities = { alarm: cfg };
    try {
      if (alarm) await api.patch(`/devices/${alarm.id}`, { capabilities });
      else await api.post(`/homes/${homeId}/devices`, {
        key: "security", name: t("security.deviceName"), adapter: "hub", protocol: "virtual", icon: "shield", capabilities });
      void qc.invalidateQueries({ queryKey: ["devices", homeId] });
      onClose();
    } catch (e) {
      setErr(e instanceof ApiError ? errorText(t, e.code, e.message) + (Array.isArray(e.details) ? ` ${(e.details as unknown[]).map(String).join("; ")}` : "") : t("errors.generic"));
    } finally { setBusy(false); }
  };
  const num = (k: "exit_delay_s" | "entry_delay_s" | "siren_max_s", label: string, min: number, max: number) => (
    <label>{label}
      <input type="number" min={min} max={max} value={cfg[k]} onChange={(e) => setCfg({ ...cfg, [k]: Number(e.target.value) })} />
    </label>
  );
  return (
    <Sheet open={open} onClose={onClose} title={t("security.setup")}>
      <form className="form" onSubmit={(e) => { e.preventDefault(); if (cfg.zones.length && !dupes) void save(); }}>
        <fieldset className="pick">
          <legend>{t("security.zones")}</legend>
          {!sensors.length && <p className="muted">{t("security.noSensors")}</p>}
          <ul className="zones">
            {sensors.map(({ d, c }) => {
              const z = zoneOf(d.key, c);
              return (
                <li key={`${d.key}.${c}`} className="zone">
                  <label className="check">
                    <input type="checkbox" checked={!!z} onChange={() => toggleZone(d.key, c)} />
                    <Icon name={c === "contact" ? "door" : "motion"} size={18} /> {d.name}
                  </label>
                  {z && (
                    <div className="row">
                      <select aria-label={`${d.name}: ${t("security.modeLabel")}`} value={z.mode}
                        onChange={(e) => patchZone(d.key, c, { mode: e.target.value as Zone["mode"] })} style={{ width: "auto" }}>
                        <option value="entry">{t("security.mode.entry")}</option>
                        <option value="instant">{t("security.mode.instant")}</option>
                      </select>
                      <label className="check">
                        <input type="checkbox" checked={z.home ?? c === "contact"} onChange={(e) => patchZone(d.key, c, { home: e.target.checked })} />
                        {t("security.alsoHome")}
                      </label>
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        </fieldset>
        <fieldset className="pick">
          <legend>{t("security.sirens")}</legend>
          <div className="chips wrap">
            {switches.map((d) => (
              <label key={d.key} className="check">
                <input type="checkbox" checked={cfg.sirens.includes(d.key)}
                  onChange={() => setCfg({ ...cfg, sirens: cfg.sirens.includes(d.key) ? cfg.sirens.filter((k) => k !== d.key) : [...cfg.sirens, d.key] })} />
                <Icon name="siren" size={16} /> {d.name}
              </label>
            ))}
          </div>
        </fieldset>
        <div className="grid">
          {num("exit_delay_s", t("security.exitDelay"), 0, 300)}
          {num("entry_delay_s", t("security.entryDelay"), 0, 300)}
          {num("siren_max_s", t("security.sirenMax"), 10, 900)}
        </div>
        <p className="note"><Icon name="shield" size={18} /> {t("security.sirenFirmware")}</p>
        {dupes && <p className="error" role="alert">{t("security.oneZonePerDevice")}</p>}
        {err && <p className="error" role="alert">{err}</p>}
        <button className="primary block" type="submit" disabled={busy || !cfg.zones.length || dupes}>{t("app.save")}</button>
      </form>
    </Sheet>
  );
}
