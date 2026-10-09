import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useSession } from "../auth/session";
import { Icon } from "../components/Icon";
import { can } from "../lib/contracts";
import { useCurrentHome } from "../lib/home";

/** "Me": profile on top, then grouped lists — the layout of the phone home apps. */
export function More() {
  const { t } = useTranslation();
  const { home } = useCurrentHome();
  const me = useSession((s) => s.me);
  const owner = can(home?.my_role, "manage_users");
  const groups: { title: string; items: { to: string; icon: string; label: string; tone: string }[] }[] = [
    { title: t("me.home"), items: [
      { to: "/rooms", icon: "rooms", label: t("nav.rooms"), tone: "tone-sensor" },
      { to: "/devices", icon: "devices", label: t("nav.devices"), tone: "tone-water" },
      { to: "/security", icon: "shield", label: t("nav.security"), tone: "tone-alert" },
      { to: "/cameras", icon: "camera", label: t("nav.cameras"), tone: "tone-camera" },
      { to: "/hub", icon: "hub", label: t("nav.hub"), tone: "tone-power" },
      ...(owner ? [{ to: "/members", icon: "members", label: t("nav.members"), tone: "tone-gate" }] : []),
    ] },
    { title: t("me.messages"), items: [
      { to: "/notifications", icon: "bell", label: t("nav.notifications"), tone: "tone-light" },
      { to: "/events", icon: "clock", label: t("nav.events"), tone: "tone-cool" },
    ] },
    { title: t("me.app"), items: [
      { to: "/settings", icon: "settings", label: t("nav.settings"), tone: "tone-neutral" },
    ] },
  ];
  const name = me?.name || me?.email || "";
  const initials = name.split(/[\s@.]+/).filter(Boolean).slice(0, 2).map((w) => w[0]!.toUpperCase()).join("");
  return (
    <div className="me">
      <Link to="/settings" className="me-card">
        <span className="me-avatar" aria-hidden="true">{initials || <Icon name="members" />}</span>
        <span className="me-who">
          <strong>{me?.name}</strong>
          <span>{me?.email}</span>
          <span className="me-home">{home?.name} · {t(`role.${home?.my_role}`, { defaultValue: home?.my_role ?? "" })}</span>
        </span>
        <Icon name="chevron" size={18} />
      </Link>
      {groups.map((g) => (
        <section key={g.title} className="me-group" aria-label={g.title}>
          <h3>{g.title}</h3>
          <div className="menu">
            {g.items.map((i) => (
              <Link key={i.to} to={i.to} className={i.tone}>
                <span className="ico"><Icon name={i.icon} /></span>
                <span style={{ flex: 1 }}>{i.label}</span>
                <Icon name="chevron" size={18} />
              </Link>
            ))}
          </div>
        </section>
      ))}
    </div>
  );
}
