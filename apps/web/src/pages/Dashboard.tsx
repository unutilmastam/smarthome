import { useTranslation } from "react-i18next";
import { useDevices } from "../api/hooks";
import { DeviceCard } from "../components/DeviceCard";
import { useLive } from "../components/Layout";
import { useCurrentHome } from "../lib/home";
import { usePrefs } from "../lib/prefs";

export function Dashboard() {
  const { t } = useTranslation();
  const { home } = useCurrentHome();
  const devices = useDevices(home?.id, useLive());
  // Select the stable map; a selector returning a fresh [] would re-render forever.
  const pinnedMap = usePrefs((s) => s.pinned);
  const pinned = pinnedMap[home?.id ?? ""] ?? [];
  if (devices.isLoading) return <p>{t("app.loading")}</p>;
  const list = devices.data ?? [];
  if (list.length === 0) return <p className="muted">{t("dashboard.noDevices")}</p>;
  const shown = pinned.length ? list.filter((d) => pinned.includes(d.id)) : list;
  return (
    <>
      <h2>{pinned.length ? t("dashboard.pinned") : t("dashboard.title")}</h2>
      {!pinned.length && <p className="muted">{t("dashboard.pinHint")}</p>}
      <div className="grid">{shown.map((d) => <DeviceCard key={d.id} device={d} role={home?.my_role} />)}</div>
    </>
  );
}
