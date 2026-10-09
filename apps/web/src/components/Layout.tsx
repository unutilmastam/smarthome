import { createContext, useContext } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useHubs, useNotifications } from "../api/hooks";
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
  const notes = useNotifications(home?.id, true, 20);
  const unacked = notes.data?.unacked ?? 0;
  const critical = (notes.data?.items ?? []).some((n) => n.severity === "critical");

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
  // Phone tab bar, like the phone home apps: home, smart (automations), electricity, me.
  const tabs = [
    { to: "/", icon: "home", label: t("nav.home"), end: true },
    { to: "/automations", icon: "play", label: t("nav.smart") },
    { to: "/energy", icon: "energy", label: t("nav.energy") },
    { to: "/more", icon: "members", label: t("nav.me") },
  ];
  const { pathname } = useLocation();

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
              <div className="home-switch">
                <h1>{home?.name ?? t("app.title")}</h1>
                {homes.length > 1 && (
                  <select aria-label={t("settings.home")} value={home?.id} onChange={(e) => setHome(e.target.value)}>
                    {homes.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
                  </select>
                )}
                <span className={`live-dot ${mode === "realtime" ? "on" : ""}`} role="img"
                  aria-label={t(mode === "realtime" ? "banner.realtime" : "banner.polling")}
                  title={t(mode === "realtime" ? "banner.realtime" : "banner.polling")} />
              </div>
            </div>
            <Link to="/notifications" className={`bell ${critical ? "alerting" : ""}`} data-testid="bell"
              aria-label={unacked ? t("notify.bellOpen", { count: unacked }) : t("notify.title")}>
              <Icon name="bell" size={20} />{unacked > 0 && <span className="badge">{unacked > 99 ? "99+" : unacked}</span>}
            </Link>
            <AddButton compact />
          </header>
          {isLocalHub() && <div className="banner info" role="status"><Icon name="wifi" />{t("banner.local")}</div>}
          {hubs.isSuccess && active.length === 0 && <div className="banner warn" role="alert"><Icon name="hub" />{t("banner.noHub")}</div>}
          {hubs.isSuccess && active.length > 0 && !hubOnline &&
            <div className="banner warn" role="alert" data-testid="hub-offline"><Icon name="offline" />{t("banner.hubOffline")}</div>}
          {/* key: every page enters with a short animation, like the phone apps */}
          <main key={pathname} className="page-enter"><Outlet /></main>
        </div>
        <AddFlowHost />
        <nav className="tabbar" aria-label="tabs">
          {tabs.map((n) => (
            <NavLink key={n.to} to={n.to} end={"end" in n ? n.end : undefined}><span className="tab-ico"><Icon name={n.icon} size={24} /></span>{n.label}</NavLink>
          ))}
        </nav>
      </div>
    </RealtimeContext.Provider>
  );
}
