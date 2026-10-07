import { useTranslation } from "react-i18next";
import type { Value } from "../api/types";
import { BADGE_ICON, valueBadge, type BadgeKind } from "../lib/status";

export function Badge({ kind, label }: { kind: BadgeKind; label?: string }) {
  const { t } = useTranslation();
  const text = label ?? t(`status.${kind}`);
  return (
    <span className={`badge ${kind}`} data-kind={kind} title={text}>
      <span aria-hidden="true">{BADGE_ICON[kind]}</span>
      <span>{text}</span>
    </span>
  );
}

export function ValueBadge({ value, pending = false }: { value?: Value; pending?: boolean }) {
  return <Badge kind={valueBadge(value, pending)} />;
}
