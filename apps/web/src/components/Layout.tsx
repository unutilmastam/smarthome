import { createContext, useContext } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useHubs } from "../api/hooks";
import { can } from "../lib/contracts";
import { useCurrentHome } from "../lib/home";
import { isLocalHub } from "../lib/local";
import { usePrefs } from "../lib/prefs";
import { useRealtime } from "../lib/realtime";
import { AddButton, AddFlowHost } from "./AddFlow";
import { Icon } from "./Icon";

export const RealtimeContext = createContext<"realtime" | "polling">("polling");
export const useLive = () => useContext(RealtimeContext) === "realtime";

function greetingKey(h = new Date().getHours()) {
  return h < 5 ? "night" : h < 12 ? "morning" : h < 18 ? "day" : h < 23 ? "evening" : "night";
}

export function Layout() {
  const { t } = useTranslation();
  const { home, homes } = useCurrentHome();
  const { setHome } = usePrefs();
  const hubs = useHubs(home?.id);
  const mode = useRealtime(home?.id);
  const active = (hubs.data ?? []).filter((h) => h.status === "active");
  const hubOnline = active.some((h) => h.online);
  const owner = can(home?.my_role, "manage_users");

  const all = [
    { to: "/", icon: "home", label: t("nav.dashboard"), end: true },
    { to: "/rooms", icon: "rooms", label: t("nav.rooms") },
    { to: "/devices", icon: "devices", label: t("nav.devices") },
    { to: "/energy", icon: "energy", label: t("nav.energy") },
    { to: "/cameras", icon: "camera", label: t("nav.cameras") },
    { to: "/security", icon: "shield", label: t("nav.security") },
    { to: "/automations", icon: "play", label: t("nav.automations") },
    { to: "/events", icon: "bell", label: t("nav.events") },
    { to: "/hub", icon: "hub", label: t("nav.hub") },
    { to: "/settings", icon: "settings", label: t("nav.settings") },
    ...(owner ? [{ to: "/members", icon: "members", label: t("nav.members") }] : []),
  ];
  const tabs = [all[0], all[1], all[2], all[3], { to: "/more", icon: "more", label: t("nav.more") }];

  return (
    <RealtimeContext.Provider value={mode}>
      <div className="app">
        <nav className="sidebar" aria-label="main">
          <div className="brand"><span className="brand-mark"><Icon name="home" size={20} /></span>SmartHome</div>
          {all.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end}><Icon name={n.icon} />{n.label}</NavLink>
          ))}
        </nav>
        <div className="shell-main">
          <header className="topbar">
            <div className="titles">
              <div className="greet">{t(`greeting.${greetingKey()}`)}</div>
              <h1>{home?.name ?? t("app.title")}</h1>
            </div>
            {homes.length > 1 && (
              <select aria-label={t("settings.home")} value={home?.id} onChange={(e) => setHome(e.target.value)} style={{ width: "auto" }}>
                {homes.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
              </select>
            )}
            <AddButton compact />
            <span className={`live ${mode === "realtime" ? "on" : ""}`} title={t(mode === "realtime" ? "banner.realtime" : "banner.polling")}>
              <i />{mode === "realtime" ? "live" : "3s"}
            </span>
          </header>
          {isLocalHub() && <div className="banner info" role="status"><Icon name="wifi" />{t("banner.local")}</div>}
          {hubs.isSuccess && active.length === 0 && <div className="banner warn" role="alert"><Icon name="hub" />{t("banner.noHub")}</div>}
          {hubs.isSuccess && active.length > 0 && !hubOnline &&
            <div className="banner warn" role="alert" data-testid="hub-offline"><Icon name="offline" />{t("banner.hubOffline")}</div>}
          <main><Outlet /></main>
        </div>
        <AddFlowHost />
        <nav className="tabbar" aria-label="tabs">
          {tabs.map((n) => (
            <NavLink key={n.to} to={n.to} end={"end" in n ? n.end : undefined}><Icon name={n.icon} size={22} />{n.label}</NavLink>
          ))}
        </nav>
      </div>
    </RealtimeContext.Provider>
  );
}
