import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useDevices, useHubs, useRooms } from "../api/hooks";
import type { Device } from "../api/types";
import { DeviceCard } from "../components/DeviceCard";
import { Icon } from "../components/Icon";
import { useLive } from "../components/Layout";
import { useCurrentHome } from "../lib/home";
import { usePrefs } from "../lib/prefs";

const good = (d: Device, cap: string, attr: string) => {
  const v = d.capabilities[cap]?.attributes[attr];
  return v && v.quality === "good" ? v.value : undefined;
};

function Stat({ icon, tone, label, value, testid }: { icon: string; tone: string; label: string; value: string; testid: string }) {
  return (
    <div className={`card stat ${tone}`} data-testid={testid}>
      <span className="ico"><Icon name={icon} size={20} /></span>
      <span className="num">{value}</span>
      <span className="muted">{label}</span>
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
      good(d, "leak", "wet") === true).length;
    return {
      // Never invent: unknown light states are not counted as "off".
      lights: known.length ? `${on}/${lights.length}` : "—",
      power: watts.length ? `${Math.round(watts.reduce((a, b) => a + b, 0))} W` : "—",
      attention,
    };
  }, [list]);
  const hubOnline = (hubs.data ?? []).some((h) => h.status === "active" && h.online);

  if (devices.isLoading) return <p>{t("app.loading")}</p>;
  if (list.length === 0) return <p className="muted">{t("dashboard.noDevices")}</p>;
  const base = pinned.length ? list.filter((d) => pinned.includes(d.id)) : list;
  const shown = room ? base.filter((d) => d.room_id === room) : base;
  return (
    <>
      <div className="stats">
        <Stat testid="stat-lights" icon="bulb" tone="tone-light" label={t("dashboard.lightsOn")} value={stats.lights} />
        <Stat testid="stat-power" icon="energy" tone="tone-power" label={t("dashboard.powerNow")} value={stats.power} />
        <Stat testid="stat-hub" icon="hub" tone={hubOnline ? "tone-gate" : "tone-alert"} label={t("dashboard.hubLabel")}
          value={hubs.isSuccess ? t(hubOnline ? "hub.online" : "hub.offline") : "—"} />
        <Stat testid="stat-attention" icon={stats.attention ? "alert" : "shield"} tone={stats.attention ? "tone-alert" : "tone-sensor"}
          label={stats.attention ? t("dashboard.attention") : t("dashboard.allGood")} value={String(stats.attention)} />
      </div>
      {(rooms.data?.length ?? 0) > 0 && (
        <div className="chips" role="group" aria-label={t("dashboard.rooms")}>
          <button aria-pressed={room === null} onClick={() => setRoom(null)}>{t("app.all")}</button>
          {rooms.data!.map((r) => (
            <button key={r.id} aria-pressed={room === r.id} onClick={() => setRoom(r.id)}>{r.name}</button>
          ))}
        </div>
      )}
      <h2>{pinned.length ? t("dashboard.pinned") : t("dashboard.title")}</h2>
      {!pinned.length && <p className="muted">{t("dashboard.pinHint")}</p>}
      <div className="grid">{shown.map((d) => <DeviceCard key={d.id} device={d} role={home?.my_role} />)}</div>
    </>
  );
}
