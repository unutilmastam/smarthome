import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { Device, Role } from "../api/types";
import { usePrefs } from "../lib/prefs";
import { DeviceControls } from "./DeviceControls";
import { Badge } from "./StatusBadge";

export function AvailabilityBadge({ device }: { device: Device }) {
  const { t } = useTranslation();
  const s = device.availability.status;
  const kind = s === "online" ? "ok" : s === "offline" ? "failed" : "unknown";
  return <Badge kind={kind} label={t(`availability.${s}`)} />;
}

export function DeviceCard({ device, role }: { device: Device; role?: Role }) {
  const { t } = useTranslation();
  const { pinned, togglePin } = usePrefs();
  const isPinned = (pinned[device.home_id] ?? []).includes(device.id);
  return (
    <article className="card" data-testid={`device-${device.key}`}>
      <div className="row spread">
        <h3><Link to={`/devices/${device.id}`}>{device.name}</Link></h3>
        <div className="row">
          <AvailabilityBadge device={device} />
          <button aria-pressed={isPinned} aria-label={isPinned ? t("dashboard.unpin") : t("dashboard.pin")}
            onClick={() => togglePin(device.home_id, device.id)} style={{ minWidth: 44, padding: 0 }}>
            {isPinned ? "★" : "☆"}
          </button>
        </div>
      </div>
      <DeviceControls device={device} role={role} compact />
    </article>
  );
}
