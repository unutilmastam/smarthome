import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useEvents } from "../api/hooks";
import { EventList } from "../components/EventFeed";
import { Icon } from "../components/Icon";
import { useCurrentHome } from "../lib/home";

const FILTERS = [
  { id: "", icon: "clock" }, { id: "critical", icon: "siren" }, { id: "warning", icon: "alert" }, { id: "info", icon: "check" },
];

export function Events() {
  const { t } = useTranslation();
  const { home } = useCurrentHome();
  const [severity, setSeverity] = useState("");
  const events = useEvents(home?.id, { severity: severity || undefined, limit: 100 });
  return (
    <>
      <h2>{t("events.title")}</h2>
      <div className="chips" role="group" aria-label={t("events.filter")}>
        {FILTERS.map((f) => (
          <button key={f.id || "all"} aria-pressed={severity === f.id} onClick={() => setSeverity(f.id)}>
            <Icon name={f.icon} size={16} /> {f.id ? t(`severity.${f.id}`) : t("app.all")}
          </button>
        ))}
      </div>
      {events.isLoading ? <p>{t("app.loading")}</p> : <div className="card"><EventList events={events.data ?? []} /></div>}
    </>
  );
}
