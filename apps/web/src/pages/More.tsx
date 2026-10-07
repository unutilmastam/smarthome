import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { Icon } from "../components/Icon";
import { can } from "../lib/contracts";
import { useCurrentHome } from "../lib/home";

export function More() {
  const { t } = useTranslation();
  const { home } = useCurrentHome();
  const items = [
    { to: "/rooms", icon: "rooms", label: t("nav.rooms"), tone: "tone-sensor" },
    { to: "/hub", icon: "hub", label: t("nav.hub"), tone: "tone-power" },
    { to: "/settings", icon: "settings", label: t("nav.settings"), tone: "tone-neutral" },
    ...(can(home?.my_role, "manage_users") ? [{ to: "/members", icon: "members", label: t("nav.members"), tone: "tone-gate" }] : []),
  ];
  return (
    <div className="menu">
      {items.map((i) => (
        <Link key={i.to} to={i.to} className={i.tone}>
          <span className="ico"><Icon name={i.icon} /></span>
          <span style={{ flex: 1 }}>{i.label}</span>
          <Icon name="chevron" size={18} />
        </Link>
      ))}
    </div>
  );
}
