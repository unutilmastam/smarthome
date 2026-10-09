import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useDevices, useRooms } from "../api/hooks";
import { useAddFlow, useCanConfigure } from "../components/AddFlow";
import { Icon } from "../components/Icon";
import { DeviceTile } from "../components/DeviceTile";
import { useLive } from "../components/Layout";
import { CAPABILITIES } from "../lib/contracts";
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
  const open = useAddFlow((s) => s.open);
  const canEdit = useCanConfigure();
  const list = useMemo(() => (devices.data ?? []).filter((d) =>
    (!q || `${d.name} ${d.key}`.toLowerCase().includes(q.toLowerCase())) &&
    (!cap || cap in d.capabilities) &&
    (!avail || d.availability.status === avail) &&
    (!room || (room === "none" ? d.room_id === null : d.room_id === room))), [devices.data, q, cap, avail, room]);
  return (
    <>
      <div className="page-head">
        <h2>{t("devices.title")}</h2>
      </div>
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
      {devices.isLoading ? <p>{t("app.loading")}</p> : !(devices.data ?? []).length ? (
        <div className="empty card">
          <span className="ico big"><Icon name="devices" size={34} /></span>
          <p>{t("dashboard.noDevices")}</p>
          {canEdit && <button className="primary" onClick={() => open("device")}><Icon name="plus" size={18} /> {t("devices.add")}</button>}
        </div>
      ) : list.length === 0 ? <p className="muted">{t("devices.noMatch")}</p> :
        <div className="dgrid">{list.map((d) => <DeviceTile key={d.id} device={d} role={home?.my_role} />)}</div>}
    </>
  );
}
