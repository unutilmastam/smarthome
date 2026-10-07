import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useDevices, useRooms } from "../api/hooks";
import type { Device } from "../api/types";
import { useAddFlow, useCanConfigure } from "../components/AddFlow";
import { DeviceCard } from "../components/DeviceCard";
import { Icon } from "../components/Icon";
import { useLive } from "../components/Layout";
import { roomIcon } from "../lib/catalog";
import { useCurrentHome } from "../lib/home";
import { deviceVisual } from "../lib/visual";

/** Active = reported on/open; unknown values are NOT counted (never invented). */
const activeCount = (list: Device[]) => list.filter((d) => deviceVisual(d).active === true).length;

export function Rooms() {
  const { t } = useTranslation();
  const { home } = useCurrentHome();
  const rooms = useRooms(home?.id);
  const devices = useDevices(home?.id, useLive());
  const open = useAddFlow((s) => s.open);
  const canEdit = useCanConfigure();
  const [sel, setSel] = useState<string | null>(null);
  if (rooms.isLoading || devices.isLoading) return <p>{t("app.loading")}</p>;
  const list = devices.data ?? [];
  const all = rooms.data ?? [];
  const noRoom = list.filter((d) => d.room_id === null);
  const groups = [
    ...all.map((r) => ({ id: r.id as string | null, name: r.name, icon: roomIcon(r), room: r })),
    ...(noRoom.length ? [{ id: null, name: t("devices.noRoom"), icon: "devices", room: undefined }] : []),
  ];
  const shown = sel === null ? groups : groups.filter((g) => (g.id ?? "none") === sel);

  return (
    <>
      <div className="page-head">
        <h2>{t("rooms.title")}</h2>
      </div>
      {!all.length && !list.length ? (
        <div className="empty card">
          <span className="ico big"><Icon name="rooms" size={34} /></span>
          <p>{t("rooms.empty")}</p>
          {canEdit && <button className="primary" onClick={() => open("room")}><Icon name="plus" size={18} /> {t("rooms.add")}</button>}
        </div>
      ) : (
        <div className="room-tiles">
          {groups.map((g) => {
            const inRoom = list.filter((d) => d.room_id === g.id);
            const on = activeCount(inRoom);
            const key = g.id ?? "none";
            return (
              <div key={key} className={`room-tile ${on ? "has-active" : ""}`} data-testid={`room-${g.name}`}>
                <button type="button" className="room-main" aria-pressed={sel === key}
                  onClick={() => setSel(sel === key ? null : key)}>
                  <span className="ico"><Icon name={g.icon} size={26} /></span>
                  <span className="room-name">{g.name}</span>
                  <span className="muted">
                    {t("rooms.deviceCount", { count: inRoom.length })}{on ? ` · ${t("rooms.activeCount", { count: on })}` : ""}
                  </span>
                </button>
                {canEdit && g.room && (
                  <button type="button" className="icon-btn room-edit" aria-label={`${t("rooms.edit")}: ${g.name}`}
                    onClick={() => open("room", { room: g.room })}><Icon name="edit" size={18} /></button>
                )}
              </div>
            );
          })}
          {canEdit && (
            <button type="button" className="room-tile add" onClick={() => open("room")}>
              <span className="ico"><Icon name="plus" size={26} /></span>
              <span className="room-name">{t("rooms.add")}</span>
            </button>
          )}
        </div>
      )}
      {shown.map((g) => {
        const inRoom = list.filter((d) => d.room_id === g.id);
        return (
          <section key={g.id ?? "none"} className="room-section">
            <div className="section-head">
              <h3><Icon name={g.icon} size={20} /> {g.name}</h3>
              {canEdit && g.id && (
                <button type="button" className="ghost" onClick={() => open("device", { defaultRoom: g.id ?? "" })}>
                  <Icon name="plus" size={16} /> {t("devices.add")}
                </button>
              )}
            </div>
            {inRoom.length ? (
              <div className="grid">{inRoom.map((d) => <DeviceCard key={d.id} device={d} role={home?.my_role} />)}</div>
            ) : <p className="muted">{t("rooms.noDevices")}</p>}
          </section>
        );
      })}
    </>
  );
}
