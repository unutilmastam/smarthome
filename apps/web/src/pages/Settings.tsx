import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../api/client";
import { qk, useSessions } from "../api/hooks";
import { useSession } from "../auth/session";
import { errorText } from "../components/CommandStatus";
import { LANGUAGES, setLanguage, type Lang } from "../i18n";
import { usePrefs } from "../lib/prefs";
import { can } from "../lib/contracts";
import { useCurrentHome } from "../lib/home";

function useAction() {
  const { t } = useTranslation();
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const run = async (fn: () => Promise<unknown>, okText: string) => {
    setMsg(null);
    try { await fn(); setMsg({ ok: true, text: okText }); return true; }
    catch (e) {
      const code = e instanceof ApiError ? e.code : "NETWORK";
      setMsg({ ok: false, text: code === "INVALID_CREDENTIALS" ? t("login.invalid") : errorText(t, code) });
      return false;
    }
  };
  const view = msg && <p className={msg.ok ? "muted" : "error"} role={msg.ok ? "status" : "alert"}>{msg.text}</p>;
  return { run, view };
}

export function Settings() {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const { theme, setTheme } = usePrefs();
  const { me, reloadMe, logout } = useSession();
  const sessions = useSessions();
  const pinAct = useAction();
  const pwAct = useAction();
  const [pinPw, setPinPw] = useState("");
  const [pin, setPin] = useState("");
  const [cur, setCur] = useState("");
  const [next, setNext] = useState("");

  return (
    <div style={{ display: "grid", gap: 16, maxWidth: 560 }}>
      <h2 style={{ margin: 0 }}>{t("settings.title")}</h2>
      <section className="card">
        <label>{t("settings.language")}
          <select value={i18n.language} onChange={(e) => setLanguage(e.target.value as Lang)}>
            {LANGUAGES.map((l) => <option key={l} value={l}>{{ uz: "O'zbekcha", ru: "Русский", en: "English" }[l]}</option>)}
          </select>
        </label>
        <label>{t("settings.theme")}
          <select value={theme} onChange={(e) => setTheme(e.target.value as typeof theme)}>
            <option value="system">{t("settings.themeSystem")}</option>
            <option value="light">{t("settings.themeLight")}</option>
            <option value="dark">{t("settings.themeDark")}</option>
          </select>
        </label>
      </section>
      <HomeLocation />

      <form className="card" onSubmit={async (e) => {
        e.preventDefault();
        if (await pinAct.run(() => api.post("/auth/pin", { password: pinPw, pin }), t("settings.pinSaved"))) {
          setPin(""); setPinPw(""); await reloadMe();
        }
      }}>
        <h3>{t("settings.pinSection")} {me?.has_pin ? "✓" : ""}</h3>
        <label>{t("settings.password")}<input type="password" autoComplete="current-password" required value={pinPw} onChange={(e) => setPinPw(e.target.value)} /></label>
        <label>{t("settings.pinNew")}<input type="password" inputMode="numeric" pattern="\d{4,8}" required value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, "").slice(0, 8))} /></label>
        {pinAct.view}
        <button className="primary" type="submit">{t("app.save")}</button>
      </form>

      <form className="card" onSubmit={async (e) => {
        e.preventDefault();
        if (await pwAct.run(() => api.post("/auth/password", { current_password: cur, new_password: next }), t("settings.passwordSaved"))) {
          setCur(""); setNext(""); void qc.invalidateQueries({ queryKey: qk.sessions });
        }
      }}>
        <h3>{t("settings.passwordSection")}</h3>
        <label>{t("settings.password")}<input type="password" autoComplete="current-password" required value={cur} onChange={(e) => setCur(e.target.value)} /></label>
        <label>{t("settings.passwordNew")}<input type="password" autoComplete="new-password" minLength={10} required value={next} onChange={(e) => setNext(e.target.value)} /></label>
        {pwAct.view}
        <button className="primary" type="submit">{t("app.save")}</button>
      </form>

      <section className="card">
        <h3>{t("settings.sessions")}</h3>
        {(sessions.data ?? []).map((s) => (
          <div key={s.id} className="row spread">
            <span>{s.current ? <strong>{t("settings.thisDevice")}</strong> : (s.user_agent ?? "—").slice(0, 40)}
              <br /><span className="muted">{s.ip ?? ""} · {new Date(s.last_used_at).toLocaleString(i18n.language)}</span></span>
            {!s.current && <button onClick={async () => { await api.del(`/auth/sessions/${s.id}`); void sessions.refetch(); }}>{t("settings.revoke")}</button>}
          </div>
        ))}
        <div className="row">
          <button onClick={() => void logout()}>{t("settings.logout")}</button>
          <button className="danger" onClick={async () => { await api.post("/auth/logout-all"); await logout(); }}>{t("settings.logoutAll")}</button>
        </div>
      </section>
    </div>
  );
}

/** Home coordinates: only used on the hub to compute sunrise/sunset (ADR 0013, H-14). */
function HomeLocation() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { home } = useCurrentHome();
  const act = useAction();
  const [lat, setLat] = useState<string>(home?.latitude?.toString() ?? "");
  const [lon, setLon] = useState<string>(home?.longitude?.toString() ?? "");
  if (!home || !can(home.my_role, "configure")) return null;
  const fromDevice = () => navigator.geolocation?.getCurrentPosition(
    (p) => { setLat(p.coords.latitude.toFixed(4)); setLon(p.coords.longitude.toFixed(4)); },
    () => undefined, { enableHighAccuracy: false, timeout: 10000 });
  return (
    <form className="card" onSubmit={async (e) => {
      e.preventDefault();
      const body = lat === "" && lon === "" ? { latitude: null, longitude: null }
        : { latitude: Number(lat), longitude: Number(lon) };
      if (await act.run(() => api.patch(`/homes/${home.id}`, body), t("settings.locationSaved"))) {
        void qc.invalidateQueries({ queryKey: qk.homes });
      }
    }}>
      <h3>{t("settings.location")}</h3>
      <p className="muted" style={{ margin: 0 }}>{t("settings.locationHint")}</p>
      <div className="grid">
        <label>{t("settings.latitude")}<input type="number" step="0.0001" min={-90} max={90} value={lat} onChange={(e) => setLat(e.target.value)} /></label>
        <label>{t("settings.longitude")}<input type="number" step="0.0001" min={-180} max={180} value={lon} onChange={(e) => setLon(e.target.value)} /></label>
      </div>
      {act.view}
      <div className="row">
        {"geolocation" in navigator && <button type="button" onClick={fromDevice}>{t("settings.useMyLocation")}</button>}
        <button className="primary" type="submit" disabled={(lat === "") !== (lon === "")}>{t("app.save")}</button>
      </div>
    </form>
  );
}
