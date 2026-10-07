import { useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useDevice, useDeviceCommands } from "../api/hooks";
import { AvailabilityBadge } from "../components/DeviceCard";
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
  if (device.isLoading) return <p>{t("app.loading")}</p>;
  if (!device.data) return <p className="error">{t("errors.generic")}</p>;
  const d = device.data;
  const fmt = (s: string) => new Date(s).toLocaleString(i18n.language, { timeZone: home?.timezone ?? "Asia/Tashkent" });
  return (
    <div style={{ display: "grid", gap: 16 }}>
      <div className="row spread"><h2 style={{ margin: 0 }}>{d.name}</h2><AvailabilityBadge device={d} /></div>
      <div className="card"><DeviceControls device={d} role={home?.my_role} /></div>
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
