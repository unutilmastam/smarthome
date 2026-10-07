import { useTranslation } from "react-i18next";
import { useDevices, useRooms } from "../api/hooks";
import { DeviceCard } from "../components/DeviceCard";
import { useLive } from "../components/Layout";
import { useCurrentHome } from "../lib/home";

export function Rooms() {
  const { t } = useTranslation();
  const { home } = useCurrentHome();
  const rooms = useRooms(home?.id);
  const devices = useDevices(home?.id, useLive());
  if (rooms.isLoading || devices.isLoading) return <p>{t("app.loading")}</p>;
  const list = devices.data ?? [];
  const groups = [...(rooms.data ?? []).map((r) => ({ id: r.id, name: r.name, type: r.type })),
    { id: null as string | null, name: t("devices.noRoom"), type: null }];
  if (!rooms.data?.length && !list.length) return <p className="muted">{t("rooms.empty")}</p>;
  return (
    <>
      <h2>{t("rooms.title")}</h2>
      {groups.map((g) => {
        const inRoom = list.filter((d) => d.room_id === g.id);
        if (!inRoom.length && g.id === null) return null;
        return (
          <section key={g.id ?? "none"} style={{ marginBottom: 20 }}>
            <h3>{g.name} {g.type && <span className="muted">· {t(`rooms.${g.type}`)}</span>}</h3>
            <div className="grid">{inRoom.map((d) => <DeviceCard key={d.id} device={d} role={home?.my_role} />)}</div>
          </section>
        );
      })}
    </>
  );
}
