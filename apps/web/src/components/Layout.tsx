import { NavLink, Outlet } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useHubs } from "../api/hooks";
import { can } from "../lib/contracts";
import { useCurrentHome } from "../lib/home";
import { isLocalHub } from "../lib/local";
import { usePrefs } from "../lib/prefs";
import { useRealtime } from "../lib/realtime";
import { createContext, useContext } from "react";

export const RealtimeContext = createContext<"realtime" | "polling">("polling");
export const useLive = () => useContext(RealtimeContext) === "realtime";

export function Layout() {
  const { t } = useTranslation();
  const { home, homes } = useCurrentHome();
  const { setHome } = usePrefs();
  const hubs = useHubs(home?.id);
  const mode = useRealtime(home?.id);
  const active = (hubs.data ?? []).filter((h) => h.status === "active");
  const hubOnline = active.some((h) => h.online);

  return (
    <RealtimeContext.Provider value={mode}>
      <div className="app">
        <header className="topbar">
          <h1>{home?.name ?? t("app.title")}</h1>
          {homes.length > 1 && (
            <select aria-label={t("settings.home")} value={home?.id} onChange={(e) => setHome(e.target.value)} style={{ width: "auto" }}>
              {homes.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
            </select>
          )}
          <span className="muted" title={t(mode === "realtime" ? "banner.realtime" : "banner.polling")}>
            {mode === "realtime" ? "● live" : "↻ 3s"}
          </span>
        </header>
        <div>
          <nav className="nav" aria-label="main">
            <NavLink to="/" end>{t("nav.dashboard")}</NavLink>
            <NavLink to="/rooms">{t("nav.rooms")}</NavLink>
            <NavLink to="/devices">{t("nav.devices")}</NavLink>
            <NavLink to="/energy">{t("nav.energy")}</NavLink>
            <NavLink to="/cameras">{t("nav.cameras")}</NavLink>
            <NavLink to="/hub">{t("nav.hub")}</NavLink>
            <NavLink to="/settings">{t("nav.settings")}</NavLink>
            {can(home?.my_role, "manage_users") && <NavLink to="/members">{t("nav.members")}</NavLink>}
          </nav>
          {isLocalHub() && <div className="banner info" role="status">{t("banner.local")}</div>}
          {hubs.isSuccess && active.length === 0 && <div className="banner warn" role="alert">{t("banner.noHub")}</div>}
          {hubs.isSuccess && active.length > 0 && !hubOnline &&
            <div className="banner warn" role="alert" data-testid="hub-offline">{t("banner.hubOffline")}</div>}
        </div>
        <main><Outlet /></main>
      </div>
    </RealtimeContext.Provider>
  );
}
