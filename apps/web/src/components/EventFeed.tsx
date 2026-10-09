import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { HomeEvent } from "../api/types";
import { useCurrentHome } from "../lib/home";
import { Icon } from "./Icon";

const CAP_ICON: Record<string, string> = {
  cover: "gate", climate: "ac", valve: "sprinkler", alarm: "shield", contact: "door", motion: "motion",
};
const SEV_ICON: Record<string, string> = { info: "check", warning: "alert", critical: "siren" };

/** One line of the event feed: colored by severity, never re-interpreted. */
export function EventItem({ e, showDevice = true }: { e: HomeEvent; showDevice?: boolean }) {
  const { t, i18n } = useTranslation();
  const { home } = useCurrentHome();
  const [cap] = e.type.split(".");
  const when = new Date(e.ts).toLocaleString(i18n.language, {
    timeZone: home?.timezone ?? "Asia/Tashkent", day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit",
  });
  const data: Record<string, unknown> = { ...e.data };
  if (typeof data.open_s === "number") data.minutes = Math.round((data.open_s as number) / 60);
  if (Array.isArray(data.open_zones)) data.zones = (data.open_zones as string[]).join(", ");
  const text = t(`event.${e.type}`, { ...data, defaultValue: e.type });
  return (
    <li className={`event sev-${e.severity}`} data-testid={`event-${e.type}`}>
      <span className="ico"><Icon name={e.severity === "info" ? CAP_ICON[cap] ?? SEV_ICON.info : SEV_ICON[e.severity]} size={20} /></span>
      <div className="event-body">
        <strong>{text}</strong>
        <span className="muted">
          {showDevice && (e.device_id
            ? <Link to={`/devices/${e.device_id}`}>{e.device_name ?? e.device_key}</Link>
            : e.device_key)}
          {showDevice && " · "}{when}
        </span>
      </div>
      <span className={`sev-chip sev-${e.severity}`}>{t(`severity.${e.severity}`)}</span>
    </li>
  );
}

export function EventList({ events, showDevice = true, empty }: { events: HomeEvent[]; showDevice?: boolean; empty?: string }) {
  const { t } = useTranslation();
  if (!events.length) return <p className="muted">{empty ?? t("events.empty")}</p>;
  return <ul className="events">{events.map((e) => <EventItem key={e.id} e={e} showDevice={showDevice} />)}</ul>;
}
