import { useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useDevice, useDeviceCommands, useRooms } from "../api/hooks";
import { useCanConfigure } from "../components/AddFlow";
import { EditDeviceSheet } from "../components/AddForms";
import { AvailabilityBadge, DeviceIcon, deviceClasses } from "../components/DeviceCard";
import { Icon } from "../components/Icon";
import { DeviceControls } from "../components/DeviceControls";
import { useLive } from "../components/Layout";
import { Badge } from "../components/StatusBadge";
import { ValueView } from "../components/ValueView";
import { useCurrentHome } from "../lib/home";
import { commandBadge } from "../lib/status";

export function DeviceDetail() {
  const { id } = useParams();
  const { t, i18n } = useTranslation();
  const { home } = useCurrentHome();
  const device = useDevice(id, useLive());
  const commands = useDeviceCommands(id);
  const rooms = useRooms(home?.id);
  const canEdit = useCanConfigure();
  const [editing, setEditing] = useState(false);
  const created = (useLocation().state as { created?: boolean } | null)?.created;
  if (device.isLoading) return <p>{t("app.loading")}</p>;
  if (!device.data) return <p className="error">{t("errors.generic")}</p>;
  const d = device.data;
  const fmt = (s: string) => new Date(s).toLocaleString(i18n.language, { timeZone: home?.timezone ?? "Asia/Tashkent" });
  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div className={`${deviceClasses(d)} detail-head`}>
        <div className="dev-head">
          <DeviceIcon device={d} size={30} />
          <div className="meta">
            <h2 style={{ margin: 0 }}>{d.name}</h2>
            <div className="row">
              <AvailabilityBadge device={d} />
              {d.room_id && <span className="muted">{rooms.data?.find((r) => r.id === d.room_id)?.name}</span>}
            </div>
          </div>
          {canEdit && (
            <button type="button" className="icon-btn" aria-label={t("devices.edit")} onClick={() => setEditing(true)}>
              <Icon name="edit" size={20} />
            </button>
          )}
        </div>
        {created && <p className="note" role="status"><Icon name="check" size={18} /> {t("devices.created")} {t("devices.afterAdd")}</p>}
        <DeviceControls device={d} role={home?.my_role} />
      </div>
      {canEdit && <EditDeviceSheet open={editing} onClose={() => setEditing(false)} device={d} rooms={rooms.data ?? []} />}
      <div className="card">
        <h3>{t("devices.attributes")}</h3>
        {Object.entries(d.capabilities).map(([cap, v]) => Object.entries(v.attributes).map(([a, val]) => (
          <ValueView key={`${cap}.${a}`} label={`${t(`cap.${cap}`)} · ${t(`attr.${a}`)}`} value={val} />
        )))}
      </div>
      <div className="card">
        <h3>{t("command.history")}</h3>
        {!commands.data?.length ? <p className="muted">{t("command.noHistory")}</p> : (
          <table>
            <thead><tr><th>{t("command.time")}</th><th>{t("command.action")}</th><th>{t("command.result")}</th></tr></thead>
            <tbody>{commands.data.map((c) => (
              <tr key={c.id}>
                <td>{fmt(c.created_at)}</td>
                <td>{t(`action.${c.action}`)}</td>
                <td><Badge kind={commandBadge(c.status)} label={t(`command.${c.status}`) + (c.reason ? ` (${c.reason})` : "")} /></td>
              </tr>))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
