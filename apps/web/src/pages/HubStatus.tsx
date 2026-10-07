import { useTranslation } from "react-i18next";
import { useHubs } from "../api/hooks";
import { Badge } from "../components/StatusBadge";
import { useCurrentHome } from "../lib/home";

export function HubStatus() {
  const { t, i18n } = useTranslation();
  const { home } = useCurrentHome();
  const hubs = useHubs(home?.id);
  if (hubs.isLoading) return <p>{t("app.loading")}</p>;
  if (!hubs.data?.length) return <p className="muted">{t("hub.none")}</p>;
  return (
    <>
      <h2>{t("hub.title")}</h2>
      <div className="grid">{hubs.data.map((h) => (
        <article key={h.id} className="card">
          <div className="row spread"><h3>{h.name}</h3>
            {h.status === "revoked" ? <Badge kind="unknown" label={t("hub.revoked")} /> :
              <Badge kind={h.online ? "ok" : "failed"} label={t(h.online ? "hub.online" : "hub.offline")} />}
          </div>
          <div className="row spread"><span className="muted">{t("hub.lastSeen")}</span>
            <span>{h.last_seen ? new Date(h.last_seen).toLocaleString(i18n.language, { timeZone: home?.timezone }) : "—"}</span></div>
          <div className="row spread"><span className="muted">{t("hub.version")}</span><span>{h.version ?? "—"}</span></div>
        </article>))}
      </div>
    </>
  );
}
