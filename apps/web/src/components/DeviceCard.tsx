import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { Device, Role } from "../api/types";
import { usePrefs } from "../lib/prefs";
import { deviceVisual } from "../lib/visual";
import { DeviceControls } from "./DeviceControls";
import { Icon } from "./Icon";
import { Badge } from "./StatusBadge";

export function AvailabilityBadge({ device }: { device: Device }) {
  const { t } = useTranslation();
  const s = device.availability.status;
  const kind = s === "online" ? "ok" : s === "offline" ? "failed" : "unknown";
  return <Badge kind={kind} label={t(`availability.${s}`)} />;
}

export function DeviceIcon({ device, size = 24 }: { device: Device; size?: number }) {
  const v = deviceVisual(device);
  return <span className="ico"><Icon name={v.icon} size={size} /></span>;
}

export function deviceClasses(device: Device): string {
  const v = deviceVisual(device);
  return ["card", "dev", `tone-${v.tone}`, v.active ? "active" : "", v.offline ? "offline" : "",
    v.anim ? `anim-${v.anim}` : ""].filter(Boolean).join(" ");
}

export function DeviceCard({ device, role }: { device: Device; role?: Role }) {
  const { t } = useTranslation();
  const { pinned, togglePin } = usePrefs();
  const isPinned = (pinned[device.home_id] ?? []).includes(device.id);
  const v = deviceVisual(device);
  return (
    <article className={deviceClasses(device)} data-testid={`device-${device.key}`}
      data-active={v.active === null ? "unknown" : String(v.active)}>
      <div className="dev-head">
        <DeviceIcon device={device} />
        <div className="meta">
          <h3><Link to={`/devices/${device.id}`}>{device.name}</Link></h3>
          <AvailabilityBadge device={device} />
        </div>
        <button className="star" aria-pressed={isPinned} aria-label={isPinned ? t("dashboard.unpin") : t("dashboard.pin")}
          onClick={() => togglePin(device.home_id, device.id)}>
          <Icon name="star" size={20} fill={isPinned ? "currentColor" : "none"} />
        </button>
      </div>
      {v.anim === "moving" && <div className="moving-bar" aria-hidden="true"><i /></div>}
      <DeviceControls device={device} role={role} compact />
    </article>
  );
}
