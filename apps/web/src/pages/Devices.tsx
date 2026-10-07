import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useDevices, useRooms } from "../api/hooks";
import { AddDeviceForm } from "../components/AddForms";
import { DeviceCard } from "../components/DeviceCard";
import { useLive } from "../components/Layout";
import { CAPABILITIES, can } from "../lib/contracts";
import { useCurrentHome } from "../lib/home";

export function Devices() {
  const { t } = useTranslation();
  const { home } = useCurrentHome();
  const devices = useDevices(home?.id, useLive());
  const rooms = useRooms(home?.id);
  const [q, setQ] = useState("");
  const [cap, setCap] = useState("");
  const [avail, setAvail] = useState("");
  const [room, setRoom] = useState("");
  const list = useMemo(() => (devices.data ?? []).filter((d) =>
    (!q || `${d.name} ${d.key}`.toLowerCase().includes(q.toLowerCase())) &&
    (!cap || cap in d.capabilities) &&
    (!avail || d.availability.status === avail) &&
    (!room || (room === "none" ? d.room_id === null : d.room_id === room))), [devices.data, q, cap, avail, room]);
  return (
    <>
      <h2>{t("devices.title")}</h2>
      <div className="grid" style={{ marginBottom: 12 }}>
        <input type="search" placeholder={t("app.search")} aria-label={t("app.search")} value={q} onChange={(e) => setQ(e.target.value)} />
        <select aria-label={t("devices.capability")} value={cap} onChange={(e) => setCap(e.target.value)}>
          <option value="">{t("devices.capability")}: {t("app.all")}</option>
          {Object.keys(CAPABILITIES).map((c) => <option key={c} value={c}>{t(`cap.${c}`)}</option>)}
        </select>
        <select aria-label={t("devices.availability")} value={avail} onChange={(e) => setAvail(e.target.value)}>
          <option value="">{t("devices.availability")}: {t("app.all")}</option>
          {["online", "offline", "unknown"].map((a) => <option key={a} value={a}>{t(`availability.${a}`)}</option>)}
        </select>
        <select aria-label={t("devices.room")} value={room} onChange={(e) => setRoom(e.target.value)}>
          <option value="">{t("devices.room")}: {t("app.all")}</option>
          {(rooms.data ?? []).map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
          <option value="none">{t("devices.noRoom")}</option>
        </select>
      </div>
      {devices.isLoading ? <p>{t("app.loading")}</p> : list.length === 0 ? <p className="muted">{t("devices.noMatch")}</p> :
        <div className="grid">{list.map((d) => <DeviceCard key={d.id} device={d} role={home?.my_role} />)}</div>}
      {home && can(home.my_role, "configure") && (
        <div style={{ marginTop: 16, maxWidth: 560 }}><AddDeviceForm homeId={home.id} rooms={rooms.data ?? []} /></div>
      )}
    </>
  );
}
