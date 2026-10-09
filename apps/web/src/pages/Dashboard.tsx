import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { groupPanels } from "../lib/panel";
import { useDevices, useHubs, useRooms } from "../api/hooks";
import type { Device } from "../api/types";
import { DeviceTile } from "../components/DeviceTile";
import { useAddFlow, useCanConfigure } from "../components/AddFlow";
import { Icon } from "../components/Icon";
import { IrrigationStop } from "../components/IrrigationStop";
import { Link } from "react-router-dom";
import { useLive } from "../components/Layout";
import { useCurrentHome } from "../lib/home";
import { usePrefs } from "../lib/prefs";

const good = (d: Device, cap: string, attr: string) => {
  const v = d.capabilities[cap]?.attributes[attr];
  return v && v.quality === "good" ? v.value : undefined;
};

/** One number in the home summary card. */
function Stat({ icon, label, value, testid }: { icon: string; label: string; value: string; testid: string }) {
  return (
    <div className="sum-stat" data-testid={testid}>
      <Icon name={icon} size={16} />
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

export function Dashboard() {
  const { t } = useTranslation();
  const { home } = useCurrentHome();
  const devices = useDevices(home?.id, useLive());
  const rooms = useRooms(home?.id);
  const hubs = useHubs(home?.id);
  // Select the stable map; a selector returning a fresh [] would re-render forever.
  const pinnedMap = usePrefs((s) => s.pinned);
  const pinned = pinnedMap[home?.id ?? ""] ?? [];
  const [room, setRoom] = useState<string | null>(null);
  const list = devices.data ?? [];

  const stats = useMemo(() => {
    const lights = list.filter((d) => "switch" in d.capabilities);
    const known = lights.filter((d) => typeof good(d, "switch", "on") === "boolean");
    const on = known.filter((d) => good(d, "switch", "on") === true).length;
    const watts = list.map((d) => good(d, "power_meter", "power")).filter((w): w is number => typeof w === "number");
    const attention = list.filter((d) => d.availability.status === "offline" ||
      good(d, "leak", "wet") === true || good(d, "breaker", "tripped") === true).length;
    // Indoor climate from a real sensor only (there is no weather service: nothing invented).
    const env = list.find((d) => typeof good(d, "environment", "temperature") === "number");
    return {
      temp: env ? Number(good(env, "environment", "temperature")) : null,
      humidity: env ? good(env, "environment", "humidity") as number | undefined : undefined,
      tempFrom: env?.name,
      // Never invent: unknown light states are not counted as "off".
      lights: known.length ? `${on}/${lights.length}` : "—",
      power: watts.length ? `${Math.round(watts.reduce((a, b) => a + b, 0))} W` : "—",
      attention,
    };
  }, [list]);
  const hubOnline = (hubs.data ?? []).some((h) => h.status === "active" && h.online);

  if (devices.isLoading) return <Skeleton />;
  if (list.length === 0) return <FirstRun />;
  // Breakers live in the panel (Elektr): on the home page only a summary, unless pinned (ADR 0015).
  const base = pinned.length ? list.filter((d) => pinned.includes(d.id)) : list.filter((d) => !d.capabilities.breaker);
  const shown = room ? base.filter((d) => d.room_id === room) : base;
  return (
    <>
      <IrrigationStop devices={list} />
      <AlarmBanner devices={list} />
      <PanelBanner devices={list} />
      <section className="sum-card" aria-label={t("dashboard.summary")}>
        <div className="sum-main">
          {stats.temp !== null ? (
            <>
              <span className="sum-big">{Math.round(stats.temp)}°</span>
              <span className="sum-sub">
                <strong>{t("dashboard.indoor")}</strong>
                <span>{stats.tempFrom}{typeof stats.humidity === "number" ? ` · ${Math.round(stats.humidity)}%` : ""}</span>
              </span>
            </>
          ) : (
            <>
              <span className="sum-icon"><Icon name={hubOnline ? "home" : "offline"} size={30} /></span>
              <span className="sum-sub">
                <strong>{stats.attention ? t("dashboard.attentionN", { count: stats.attention }) : t("dashboard.allGood")}</strong>
                <span>{t("dashboard.devicesCount", { count: list.length })}</span>
              </span>
            </>
          )}
        </div>
        <div className="stats">
          <Stat testid="stat-lights" icon="bulb" label={t("dashboard.lightsOn")} value={stats.lights} />
          <Stat testid="stat-power" icon="energy" label={t("dashboard.powerNow")} value={stats.power} />
          <Stat testid="stat-hub" icon="hub" label={t("dashboard.hubLabel")}
            value={hubs.isSuccess ? t(hubOnline ? "hub.online" : "hub.offline") : "—"} />
          <Stat testid="stat-attention" icon={stats.attention ? "alert" : "shield"}
            label={stats.attention ? t("dashboard.attention") : t("dashboard.allGood")} value={String(stats.attention)} />
        </div>
      </section>
      <nav className="room-tabs" aria-label={t("dashboard.rooms")}>
        <button aria-pressed={room === null} onClick={() => setRoom(null)}>
          {pinned.length ? t("dashboard.pinned") : t("dashboard.allDevices")}</button>
        {(rooms.data ?? []).map((r) => (
          <button key={r.id} aria-pressed={room === r.id} onClick={() => setRoom(r.id)}>{r.name}</button>
        ))}
        <Link to="/rooms" className="room-tabs-more" aria-label={t("nav.rooms")}><Icon name="more" size={20} /></Link>
      </nav>
      <div className="dgrid">{shown.map((d) => <DeviceTile key={d.id} device={d} role={home?.my_role} />)}</div>
      {!pinned.length && <p className="muted hint">{t("dashboard.pinHint")}</p>}
    </>
  );
}

function FirstRun() {
  const { t } = useTranslation();
  const open = useAddFlow((s) => s.open);
  const canEdit = useCanConfigure();
  return (
    <div className="empty card hero">
      <span className="ico big"><Icon name="home" size={36} /></span>
      <h2>{t("dashboard.welcome")}</h2>
      <p className="muted">{t("dashboard.noDevices")}</p>
      {canEdit && (
        <div className="row" style={{ justifyContent: "center" }}>
          <button className="primary" onClick={() => open("room")}><Icon name="rooms" size={18} /> {t("rooms.add")}</button>
          <button className="primary" onClick={() => open("device")}><Icon name="plus" size={18} /> {t("devices.add")}</button>
        </div>
      )}
    </div>
  );
}

/** Security state at a glance; links to the security page. Shows only a REPORTED state. */
function AlarmBanner({ devices }: { devices: Device[] }) {
  const { t } = useTranslation();
  const alarm = devices.find((d) => "alarm" in d.capabilities);
  const v = alarm?.capabilities.alarm.attributes.state;
  if (!alarm || !v || (v.quality !== "good" && v.quality !== "stale")) return null;
  const st = String(v.value);
  return (
    <Link to="/security" className={`banner alarm-banner state-${st}`} data-testid="alarm-banner">
      <Icon name={st === "disarmed" ? "unlock" : "shield"} />
      <span style={{ flex: 1 }}>{t("security.title")}: <strong>{t(`enum.${st}`, { defaultValue: st })}</strong></span>
      <Icon name="chevron" size={18} />
    </Link>
  );
}

/** Electrical panel at a glance (ADR 0015): only reported states; tripped breakers named. */
function PanelBanner({ devices }: { devices: Device[] }) {
  const { t } = useTranslation();
  const items = groupPanels(devices).flatMap((p) => p.items);
  if (!items.length) return null;
  const tripped = items.filter((i) => i.state === "tripped");
  const on = items.filter((i) => i.state === "on").length;
  return (
    <Link to="/energy" className={`banner alarm-banner panel-banner ${tripped.length ? "state-triggered" : ""}`} data-testid="panel-banner">
      <Icon name={tripped.length ? "alert" : "breaker"} />
      <span style={{ flex: 1 }}>
        {t("panel.title")}: <strong>{tripped.length
          ? t("panel.bannerTripped", { names: tripped.map((i) => i.device.name).join(", ") })
          : t("panel.bannerOk", { on, total: items.length })}</strong>
      </span>
      <Icon name="chevron" size={18} />
    </Link>
  );
}

/** Grey placeholder cards while the first data loads (no fake values). */
function Skeleton() {
  const { t } = useTranslation();
  return (
    <div aria-busy="true" aria-label={t("app.loading")}>
      <div className="sum-card skeleton" />
      <div className="dgrid">{[0, 1, 2, 3].map((i) => <div key={i} className="dtile skeleton" />)}</div>
    </div>
  );
}
