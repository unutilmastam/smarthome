import { useEffect, useMemo, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../api/client";
import type { Device, Room } from "../api/types";
import { DEVICE_ICONS, DEVICE_TYPES, KEY_RE, ROOM_ICONS, roomIcon, suggestKey, type DeviceType } from "../lib/catalog";
import { CAPABILITIES } from "../lib/contracts";
import { groupPanels, nextPosition } from "../lib/panel";
import type { DevicePreset } from "./AddFlow";
import { errorText } from "./CommandStatus";
import { Icon } from "./Icon";
import { IconPicker, Sheet } from "./Sheet";

function useSubmit() {
  const { t } = useTranslation();
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const run = async <T,>(fn: () => Promise<T>): Promise<T | undefined> => {
    setErr(null); setBusy(true);
    try { return await fn(); }
    catch (e) {
      if (e instanceof ApiError) {
        const details = Array.isArray(e.details) ? ` ${(e.details as unknown[]).map(String).join("; ")}` : "";
        setErr(errorText(t, e.code, e.message) + details);
      } else setErr(t("errors.generic"));
      return undefined;
    } finally { setBusy(false); }
  };
  const view = err ? <p className="error" role="alert">{err}</p> : null;
  return { run, view, busy, reset: () => setErr(null) };
}

/** Room chooser as chips with room icons ("" = no room). */
function RoomChips({ rooms, value, onChange }: { rooms: Room[]; value: string; onChange: (v: string) => void }) {
  const { t } = useTranslation();
  const opts = [{ id: "", name: t("devices.noRoom"), icon: "close" }, ...rooms.map((r) => ({ id: r.id, name: r.name, icon: roomIcon(r) }))];
  return (
    <fieldset className="pick">
      <legend>{t("devices.room")}</legend>
      <div className="chips wrap" role="radiogroup" aria-label={t("devices.room")}>
        {opts.map((o) => (
          <button key={o.id || "none"} type="button" role="radio" aria-checked={value === o.id} onClick={() => onChange(o.id)}>
            <Icon name={o.icon} size={16} /> {o.name}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

// ---- add device --------------------------------------------------------------------

/** Nominal currents allowed by the contract (capabilities.json -> breaker.config.rating_a). */
const RATINGS: number[] = (CAPABILITIES.breaker as unknown as {
  config: { properties: { rating_a: { enum: number[] } } } }).config.properties.rating_a.enum;

export function AddDeviceSheet({ open, onClose, homeId, rooms, devices, defaultRoom = "", preset }: {
  open: boolean; onClose: () => void; homeId: string; rooms: Room[]; devices: Device[]; defaultRoom?: string;
  preset?: DevicePreset;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { run, view, busy, reset } = useSubmit();
  const [type, setType] = useState<DeviceType | null>(null);
  const [name, setName] = useState("");
  const [icon, setIcon] = useState("bulb");
  const [room, setRoom] = useState(defaultRoom);
  const [key, setKey] = useState("");
  const [keyTouched, setKeyTouched] = useState(false);
  const [caps, setCaps] = useState<string[]>(["switch"]);
  const [maxRuntime, setMaxRuntime] = useState("");
  // Breaker in the electrical panel (ADR 0015)
  const [panel, setPanel] = useState("");
  const [position, setPosition] = useState("");
  const [rating, setRating] = useState("");
  const [curve, setCurve] = useState("");
  const [poles, setPoles] = useState("1");
  const [metered, setMetered] = useState(false);
  const taken = useMemo(() => devices.map((d) => d.key), [devices]);
  const panels = useMemo(() => groupPanels(devices), [devices]);
  const isBreaker = caps.includes("breaker");
  const keyFor = (n: string) => suggestKey(isBreaker || type?.id === "breaker" ? `avtomat ${n}` : n, taken);

  const freePosition = (p: string) => String(nextPosition(panels.find((x) => x.panel === p.trim())?.items ?? []));

  const choose = (dt: DeviceType, pre?: DevicePreset) => {
    setType(dt); setIcon(dt.icon); setCaps(dt.caps ?? ["switch"]);
    if (dt.id === "breaker") {
      // A breaker is named after its circuit ("Oshxona"), not after its type.
      const p = pre?.panel ?? panels[0]?.panel ?? "";
      setName(""); setKey(""); setPanel(p);
      setPosition(pre?.position ? String(pre.position) : freePosition(p));
      return;
    }
    const n = dt.id === "custom" ? "" : t(`dtype.${dt.id}`);
    setName(n);
    if (!keyTouched) setKey(n ? suggestKey(n, taken) : "");
  };

  useEffect(() => {
    if (!open) return;
    setType(null); setName(""); setKey(""); setKeyTouched(false); setMaxRuntime(""); setRoom(defaultRoom); reset();
    setPanel(""); setPosition(""); setRating(""); setCurve(""); setPoles("1"); setMetered(false);
    const dt = preset && DEVICE_TYPES.find((x) => x.id === preset.type);
    if (dt) choose(dt, preset);
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps

  const onName = (n: string) => { setName(n); if (!keyTouched) setKey(n.trim() ? keyFor(n) : ""); };
  const toggleCap = (c: string) => setCaps(caps.includes(c) ? caps.filter((x) => x !== c) : [...caps, c]);
  const needsRuntime = caps.includes("valve");
  const keyOk = KEY_RE.test(key);
  const pos = Number(position);
  const positionOk = !isBreaker || (Number.isInteger(pos) && pos >= 1 && pos <= 99);
  const valid = !!name.trim() && keyOk && caps.length > 0 && (!needsRuntime || Number(maxRuntime) >= 1) && positionOk;

  const submit = async () => {
    const capabilities: Record<string, Record<string, number | string>> = {};
    for (const c of caps) capabilities[c] = {};
    if (needsRuntime) capabilities.valve = { max_runtime_s: Number(maxRuntime) };
    if (isBreaker) {
      const cfg: Record<string, number | string> = { position: pos, poles: Number(poles) };
      if (panel.trim()) cfg.panel = panel.trim();
      if (rating) cfg.rating_a = Number(rating);
      if (curve) cfg.curve = curve;
      capabilities.breaker = cfg;
      if (metered) capabilities.power_meter = {};
    }
    const body: Record<string, unknown> = { key, name: name.trim(), adapter: "esphome", protocol: "mqtt", capabilities, icon };
    if (room) body.room_id = room;
    const created = await run(() => api.post<Device>(`/homes/${homeId}/devices`, body));
    if (created) {
      void qc.invalidateQueries({ queryKey: ["devices", homeId] });
      onClose();
      if (created.id) navigate(`/devices/${created.id}`, { state: { created: true } });
    }
  };

  return (
    <Sheet open={open} onClose={onClose} title={type ? t("devices.add") : t("devices.pickType")}
      onBack={type ? () => setType(null) : undefined}>
      {!type ? (
        <div className="tiles">
          {DEVICE_TYPES.map((dt) => (
            <button key={dt.id} type="button" className="tile" onClick={() => choose(dt)}>
              <span className="ico"><Icon name={dt.icon} size={26} /></span>
              <span>{t(`dtype.${dt.id}`)}</span>
            </button>
          ))}
        </div>
      ) : (
        <form className="form" onSubmit={(e) => { e.preventDefault(); if (valid) void submit(); }}>
          <div className="preview">
            <span className="ico big"><Icon name={icon} size={34} /></span>
            <div>
              <strong>{name || t("devices.name")}</strong>
              <div className="muted">{caps.map((c) => t(`cap.${c}`)).join(" · ")}</div>
            </div>
          </div>
          <label>{isBreaker ? t("devices.breakerName") : t("devices.name")}
            <input required maxLength={120} value={name} onChange={(e) => onName(e.target.value)}
              placeholder={isBreaker ? t("devices.breakerNamePh") : undefined} />
          </label>
          {isBreaker && (
            <fieldset className="pick breaker-fields">
              <legend>{t("panel.title")}</legend>
              <label>{t("devices.panel")}
                <input list="panel-names" maxLength={40} value={panel} placeholder={t("panel.default")}
                  onChange={(e) => { setPanel(e.target.value); setPosition(freePosition(e.target.value)); }} />
                <datalist id="panel-names">{panels.filter((p) => p.panel).map((p) => <option key={p.panel} value={p.panel} />)}</datalist>
              </label>
              <div className="row2">
                <label>{t("devices.position")}
                  <input type="number" inputMode="numeric" required min={1} max={99} value={position}
                    aria-invalid={!positionOk} onChange={(e) => setPosition(e.target.value)} />
                </label>
                <label>{t("devices.poles")}
                  <select value={poles} onChange={(e) => setPoles(e.target.value)}>
                    {[1, 2, 3, 4].map((p) => <option key={p} value={p}>{p}P</option>)}
                  </select>
                </label>
              </div>
              <div className="row2">
                <label>{t("devices.curve")}
                  <select value={curve} onChange={(e) => setCurve(e.target.value)}>
                    <option value="">{t("devices.notSet")}</option>
                    {["B", "C", "D"].map((c) => <option key={c} value={c}>{c}</option>)}
                  </select>
                </label>
                <label>{t("devices.rating")}
                  <select value={rating} onChange={(e) => setRating(e.target.value)}>
                    <option value="">{t("devices.notSet")}</option>
                    {RATINGS.map((r) => <option key={r} value={r}>{r} A</option>)}
                  </select>
                </label>
              </div>
              <label className="check">
                <input type="checkbox" checked={metered} onChange={(e) => setMetered(e.target.checked)} />
                {t("devices.metered")}
              </label>
              <p className="muted" style={{ margin: 0 }}>{t("devices.breakerNote")}</p>
            </fieldset>
          )}
          <RoomChips rooms={rooms} value={room} onChange={setRoom} />
          <IconPicker icons={DEVICE_ICONS} value={icon} onChange={setIcon} label={t("devices.icon")} labelFor={(i) => t(`icon.${i}`)} />
          {type.caps === null && (
            <fieldset className="pick">
              <legend>{t("devices.capabilities")}</legend>
              <div className="chips wrap">
                {Object.keys(CAPABILITIES).map((c) => (
                  <label key={c} className="check">
                    <input type="checkbox" checked={caps.includes(c)} onChange={() => toggleCap(c)} />
                    {t(`cap.${c}`)}
                  </label>))}
              </div>
            </fieldset>
          )}
          {needsRuntime && (
            <label>{t("devices.maxRuntime")}
              <input type="number" required min={1} max={3600} value={maxRuntime} onChange={(e) => setMaxRuntime(e.target.value)} />
            </label>
          )}
          <label>{t("devices.key")}
            <input required value={key} autoCapitalize="none" spellCheck={false} aria-invalid={!!key && !keyOk}
              onChange={(e) => { setKeyTouched(true); setKey(e.target.value.trim()); }} />
            <span className="muted">{t("devices.keyHint")}</span>
          </label>
          <p className="note"><Icon name="hub" size={18} /> {t("devices.afterAdd")}</p>
          {view}
          <button className="primary block" type="submit" disabled={!valid || busy}>
            <Icon name="plus" size={18} /> {t("app.add")}
          </button>
        </form>
      )}
    </Sheet>
  );
}

// ---- edit device -------------------------------------------------------------------

export function EditDeviceSheet({ open, onClose, device, rooms }: {
  open: boolean; onClose: () => void; device: Device; rooms: Room[];
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const navigate = useNavigate();
  const { run, view, busy } = useSubmit();
  const [name, setName] = useState(device.name);
  const [icon, setIcon] = useState(device.icon ?? "");
  const [room, setRoom] = useState(device.room_id ?? "");
  const [confirmDel, setConfirmDel] = useState(false);
  useEffect(() => {
    if (open) { setName(device.name); setIcon(device.icon ?? ""); setRoom(device.room_id ?? ""); setConfirmDel(false); }
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps
  const refresh = () => {
    void qc.invalidateQueries({ queryKey: ["devices", device.home_id] });
    void qc.invalidateQueries({ queryKey: ["device", device.id] });
  };
  const save = async () => {
    const res = await run(() => api.patch(`/devices/${device.id}`, { name: name.trim(), icon: icon || null, room_id: room || null }));
    if (res !== undefined) { refresh(); onClose(); }
  };
  const remove = async () => {
    const res = await run(() => api.del(`/devices/${device.id}`));
    if (res !== undefined) { refresh(); onClose(); navigate("/devices"); }
  };
  return (
    <Sheet open={open} onClose={onClose} title={t("devices.edit")}>
      <form className="form" onSubmit={(e) => { e.preventDefault(); if (name.trim()) void save(); }}>
        <label>{t("devices.name")}<input required maxLength={120} value={name} onChange={(e) => setName(e.target.value)} /></label>
        <RoomChips rooms={rooms} value={room} onChange={setRoom} />
        <IconPicker icons={DEVICE_ICONS} value={icon} onChange={setIcon} label={t("devices.icon")} labelFor={(i) => t(`icon.${i}`)} />
        <p className="muted" style={{ margin: 0 }}>{t("devices.keyReadonly", { key: device.key })}</p>
        {view}
        <button className="primary block" type="submit" disabled={busy || !name.trim()}>{t("app.save")}</button>
        <div className="danger-zone">
          {!confirmDel ? (
            <button type="button" className="danger" onClick={() => setConfirmDel(true)}>
              <Icon name="trash" size={18} /> {t("devices.remove")}
            </button>
          ) : (
            <>
              <p role="alert" style={{ margin: 0 }}>{t("devices.removeConfirm", { name: device.name })}</p>
              <div className="row">
                <button type="button" onClick={() => setConfirmDel(false)}>{t("app.cancel")}</button>
                <button type="button" className="danger" disabled={busy} onClick={() => void remove()}>
                  <Icon name="trash" size={18} /> {t("devices.removeYes")}
                </button>
              </div>
            </>
          )}
        </div>
      </form>
    </Sheet>
  );
}

// ---- rooms (sections) ------------------------------------------------------------------

export function RoomSheet({ open, onClose, homeId, room }: {
  open: boolean; onClose: () => void; homeId: string; room?: Room;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { run, view, busy } = useSubmit();
  const [name, setName] = useState("");
  const [type, setType] = useState<"indoor" | "outdoor">("indoor");
  const [icon, setIcon] = useState("sofa");
  const [confirmDel, setConfirmDel] = useState(false);
  useEffect(() => {
    if (!open) return;
    setName(room?.name ?? ""); setType(room?.type ?? "indoor"); setIcon(room ? roomIcon(room) : "sofa"); setConfirmDel(false);
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps
  const done = () => {
    void qc.invalidateQueries({ queryKey: ["rooms", homeId] });
    void qc.invalidateQueries({ queryKey: ["devices", homeId] });
    onClose();
  };
  const save = async () => {
    const body = { name: name.trim(), type, icon };
    const res = await run(() => (room ? api.patch(`/rooms/${room.id}`, body) : api.post(`/homes/${homeId}/rooms`, body)));
    if (res !== undefined) done();
  };
  const remove = async () => {
    if (!room) return;
    const res = await run(() => api.del(`/rooms/${room.id}`));
    if (res !== undefined) done();
  };
  return (
    <Sheet open={open} onClose={onClose} title={room ? t("rooms.edit") : t("rooms.add")}>
      <form className="form" onSubmit={(e) => { e.preventDefault(); if (name.trim()) void save(); }}>
        <div className="preview">
          <span className="ico big"><Icon name={icon} size={34} /></span>
          <strong>{name || t("rooms.name")}</strong>
        </div>
        <label>{t("rooms.name")}<input required maxLength={120} value={name} onChange={(e) => setName(e.target.value)} /></label>
        <div className="seg" role="radiogroup" aria-label={t("rooms.type")}>
          {(["indoor", "outdoor"] as const).map((v) => (
            <button key={v} type="button" role="radio" aria-checked={type === v} className={type === v ? "primary" : ""}
              onClick={() => setType(v)}>{t(`rooms.${v}`)}</button>
          ))}
        </div>
        <IconPicker icons={ROOM_ICONS} value={icon} onChange={setIcon} label={t("rooms.icon")} labelFor={(i) => t(`icon.${i}`)} />
        {view}
        <button className="primary block" type="submit" disabled={busy || !name.trim()}>
          {room ? t("app.save") : <><Icon name="plus" size={18} /> {t("app.add")}</>}
        </button>
        {room && (
          <div className="danger-zone">
            {!confirmDel ? (
              <button type="button" className="danger" onClick={() => setConfirmDel(true)}>
                <Icon name="trash" size={18} /> {t("rooms.remove")}
              </button>
            ) : (
              <>
                <p role="alert" style={{ margin: 0 }}>{t("rooms.removeConfirm", { name: room.name })}</p>
                <div className="row">
                  <button type="button" onClick={() => setConfirmDel(false)}>{t("app.cancel")}</button>
                  <button type="button" className="danger" disabled={busy} onClick={() => void remove()}>
                    <Icon name="trash" size={18} /> {t("rooms.removeYes")}
                  </button>
                </div>
              </>
            )}
          </div>
        )}
      </form>
    </Sheet>
  );
}

/** "+" menu: what to add. */
export function AddMenuSheet({ open, onClose, onDevice, onRoom }: {
  open: boolean; onClose: () => void; onDevice: () => void; onRoom: () => void;
}) {
  const { t } = useTranslation();
  return (
    <Sheet open={open} onClose={onClose} title={t("add.title")}>
      <div className="tiles two">
        <button type="button" className="tile big" onClick={onDevice}>
          <span className="ico"><Icon name="devices" size={30} /></span>
          <span><strong>{t("devices.add")}</strong><small className="muted">{t("add.deviceHint")}</small></span>
        </button>
        <button type="button" className="tile big" onClick={onRoom}>
          <span className="ico"><Icon name="rooms" size={30} /></span>
          <span><strong>{t("rooms.add")}</strong><small className="muted">{t("add.roomHint")}</small></span>
        </button>
      </div>
    </Sheet>
  );
}
