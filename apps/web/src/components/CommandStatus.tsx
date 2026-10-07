import { useTranslation } from "react-i18next";
import type { Tracked } from "../lib/commands";
import { commandBadge } from "../lib/status";
import { Badge } from "./StatusBadge";

export function errorText(t: (k: string, o?: Record<string, unknown>) => string, code?: string, fallback?: string) {
  if (!code) return fallback ?? t("errors.generic");
  return t(`errors.${code}`, { defaultValue: fallback ?? t("errors.generic") });
}

export function CommandStatus({ tracked }: { tracked: Tracked | null }) {
  const { t } = useTranslation();
  if (!tracked) return null;
  if (tracked.status === "error") {
    return <p className="error" role="alert">{errorText(t, tracked.error?.code, tracked.error?.message)}</p>;
  }
  if (tracked.status === "sending") return <Badge kind="pending" label={t("command.sending")} />;
  const label = t(`command.${tracked.status}`) +
    (tracked.reason ? ` (${tracked.reason})` : "");
  return <span role="status" data-testid="command-status" data-status={tracked.status}><Badge kind={commandBadge(tracked.status)} label={label} /></span>;
}
