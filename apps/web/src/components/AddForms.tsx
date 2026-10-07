import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../api/client";
import type { Room } from "../api/types";
import { CAPABILITIES } from "../lib/contracts";
import { errorText } from "./CommandStatus";

function useSubmit() {
  const { t } = useTranslation();
  const [err, setErr] = useState<string | null>(null);
  const [okMsg, setOk] = useState<string | null>(null);
  const run = async (fn: () => Promise<unknown>, ok: string) => {
    setErr(null); setOk(null);
    try { await fn(); setOk(ok); return true; }
    catch (e) {
      if (e instanceof ApiError) {
        const details = Array.isArray(e.details) ? ` ${(e.details as unknown[]).map(String).join("; ")}` : "";
        setErr(errorText(t, e.code, e.message) + details);
      } else setErr(t("errors.generic"));
      return false;
    }
  };
  const view = <>{err && <p className="error" role="alert">{err}</p>}{okMsg && <p className="muted" role="status">{okMsg}</p>}</>;
  return { run, view };
}

export function AddRoomForm({ homeId }: { homeId: string }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { run, view } = useSubmit();
  const [name, setName] = useState("");
  const [type, setType] = useState<"indoor" | "outdoor">("indoor");
  return (
    <form className="card" onSubmit={async (e) => {
      e.preventDefault();
      if (await run(() => api.post(`/homes/${homeId}/rooms`, { name, type }), name)) {
        setName(""); void qc.invalidateQueries({ queryKey: ["rooms", homeId] });
      }
    }}>
      <h3>{t("rooms.add")}</h3>
      <label>{t("rooms.name")}<input required maxLength={120} value={name} onChange={(e) => setName(e.target.value)} /></label>
      <label>{t("rooms.type")}
        <select value={type} onChange={(e) => setType(e.target.value as "indoor" | "outdoor")}>
          <option value="indoor">{t("rooms.indoor")}</option>
          <option value="outdoor">{t("rooms.outdoor")}</option>
        </select>
      </label>
      {view}
      <button className="primary" type="submit">{t("app.add")}</button>
    </form>
  );
}

export function AddDeviceForm({ homeId, rooms }: { homeId: string; rooms: Room[] }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { run, view } = useSubmit();
  const [key, setKey] = useState("");
  const [name, setName] = useState("");
  const [room, setRoom] = useState("");
  const [caps, setCaps] = useState<string[]>(["switch"]);
  const [maxRuntime, setMaxRuntime] = useState("");
  const toggle = (c: string) => setCaps(caps.includes(c) ? caps.filter((x) => x !== c) : [...caps, c]);
  const needsRuntime = caps.includes("valve");
  return (
    <form className="card" onSubmit={async (e) => {
      e.preventDefault();
      const capabilities: Record<string, Record<string, number>> = {};
      for (const c of caps) capabilities[c] = {};
      if (needsRuntime) capabilities.valve = { max_runtime_s: Number(maxRuntime) };
      const body: Record<string, unknown> = { key, name, adapter: "esphome", protocol: "mqtt", capabilities };
      if (room) body.room_id = room;
      if (await run(() => api.post(`/homes/${homeId}/devices`, body), t("devices.created"))) {
        setKey(""); setName(""); void qc.invalidateQueries({ queryKey: ["devices", homeId] });
      }
    }}>
      <h3>{t("devices.add")}</h3>
      <label>{t("devices.key")}
        <input required pattern="[a-z][a-z0-9_]{1,63}" value={key} onChange={(e) => setKey(e.target.value.trim())} autoCapitalize="none" />
        <span className="muted">{t("devices.keyHint")}</span>
      </label>
      <label>{t("devices.name")}<input required maxLength={120} value={name} onChange={(e) => setName(e.target.value)} /></label>
      <label>{t("devices.room")}
        <select value={room} onChange={(e) => setRoom(e.target.value)}>
          <option value="">{t("devices.noRoom")}</option>
          {rooms.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
        </select>
      </label>
      <fieldset style={{ border: 0, padding: 0, display: "grid", gap: 6 }}>
        <legend className="muted">{t("devices.capabilities")}</legend>
        <div className="row">{Object.keys(CAPABILITIES).map((c) => (
          <label key={c} className="row" style={{ display: "flex", color: "var(--text)" }}>
            <input type="checkbox" style={{ width: 20, minHeight: 20 }} checked={caps.includes(c)} onChange={() => toggle(c)} />
            {t(`cap.${c}`)}
          </label>))}
        </div>
      </fieldset>
      {needsRuntime && (
        <label>{t("devices.maxRuntime")}
          <input type="number" required min={1} max={3600} value={maxRuntime} onChange={(e) => setMaxRuntime(e.target.value)} />
        </label>
      )}
      {view}
      <button className="primary" type="submit" disabled={caps.length === 0}>{t("app.add")}</button>
    </form>
  );
}
