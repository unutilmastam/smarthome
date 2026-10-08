import { useState } from "react";
import { Link } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../api/client";
import { useDevices, useNotifications } from "../api/hooks";
import type { AppNotification, Device } from "../api/types";
import { errorText } from "../components/CommandStatus";
import { Icon } from "../components/Icon";
import { can } from "../lib/contracts";
import { useCurrentHome } from "../lib/home";

const SEV_ICON: Record<string, string> = { info: "check", warning: "alert", critical: "siren" };
const KIND_ICON: Record<string, string> = { hub: "hub", device: "offline", automation: "play", test: "send" };

type T = (k: string, o?: Record<string, unknown>) => string;

/** Same words as the event feed / Telegram; the server's Uzbek title is the fallback. */
export function notificationText(t: T, n: AppNotification, devices: Device[]): string {
  const name = (k: unknown) => devices.find((d) => d.key === k)?.name ?? String(k);
  const d: Record<string, unknown> = { ...n.data };
  if (n.source === "event") {
    if (typeof d.open_s === "number") d.minutes = Math.round(d.open_s / 60);
    if (Array.isArray(d.open_zones)) d.zones = (d.open_zones as string[]).map(name).join(", ");
    if (typeof d.zone === "string") d.zone = name(d.zone);
    return t(`event.${n.kind}`, { ...d, defaultValue: n.title });
  }
  if (n.source === "automation") return n.title;
  return t(`notify.kind.${n.kind}`, { ...d, defaultValue: n.title });
}

export function NotificationItem({ n, devices, canAck }: { n: AppNotification; devices: Device[]; canAck: boolean }) {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const { home } = useCurrentHome();
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const fmt = (iso: string) => new Date(iso).toLocaleString(i18n.language, {
    timeZone: home?.timezone ?? "Asia/Tashkent", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  const ack = async () => {
    setBusy(true); setErr(null);
    try {
      await api.post(`/notifications/${n.id}/ack`);
      await qc.invalidateQueries({ queryKey: ["notifications"] });
    } catch (e) { setErr(errorText(t, e instanceof ApiError ? e.code : "NETWORK")); }
    finally { setBusy(false); }
  };
  const icon = n.severity === "info" ? KIND_ICON[n.source] ?? SEV_ICON.info : SEV_ICON[n.severity];
  return (
    <li className={`event sev-${n.severity} ${n.needs_ack && !n.acked_at ? "unacked" : ""}`} data-testid={`notification-${n.kind}`}>
      <span className="ico"><Icon name={icon} size={20} /></span>
      <div className="event-body">
        <strong>{notificationText(t, n, devices)}</strong>
        <span className="muted">
          {n.body && n.source !== "event" ? `${n.body.replace(/^\S+\s/, "")} · ` : ""}
          {n.source === "event" && typeof n.data.device_key === "string" ? `${devices.find((d) => d.key === n.data.device_key)?.name ?? n.data.device_key} · ` : ""}
          {fmt(n.ts)}
        </span>
        {n.acked_at && <span className="muted acked"><Icon name="check" size={14} /> {t("notify.ackedBy", { name: n.acked_by_name ?? "—", time: fmt(n.acked_at) })}</span>}
        {err && <span className="error" role="alert">{err}</span>}
      </div>
      {n.needs_ack && !n.acked_at && canAck
        ? <button className="primary small" disabled={busy} onClick={() => void ack()}>{t("notify.ack")}</button>
        : <span className={`sev-chip sev-${n.severity}`}>{t(`severity.${n.severity}`)}</span>}
    </li>
  );
}

export function Notifications() {
  const { t } = useTranslation();
  const { home } = useCurrentHome();
  const [onlyOpen, setOnlyOpen] = useState(false);
  const list = useNotifications(home?.id, onlyOpen);
  const devices = useDevices(home?.id);
  // Same rule as the server: owner/admin/family receive and acknowledge.
  const canAck = can(home?.my_role, "control_basic");
  const items = list.data?.items ?? [];
  return (
    <>
      <div className="row spread">
        <h2>{t("notify.title")}</h2>
        <Link to="/settings#notifications" className="btn"><Icon name="settings" size={16} /> {t("notify.channels")}</Link>
      </div>
      <div className="chips" role="group" aria-label={t("events.filter")}>
        <button aria-pressed={!onlyOpen} onClick={() => setOnlyOpen(false)}><Icon name="clock" size={16} /> {t("app.all")}</button>
        <button aria-pressed={onlyOpen} onClick={() => setOnlyOpen(true)}>
          <Icon name="alert" size={16} /> {t("notify.open")}{list.data?.unacked ? ` (${list.data.unacked})` : ""}
        </button>
      </div>
      {list.isLoading ? <p>{t("app.loading")}</p> : (
        <div className="card">
          {items.length === 0
            ? <p className="muted">{t(onlyOpen ? "notify.allSeen" : "notify.empty")}</p>
            : <ul className="events">{items.map((n) => <NotificationItem key={n.id} n={n} devices={devices.data ?? []} canAck={canAck} />)}</ul>}
        </div>
      )}
    </>
  );
}
