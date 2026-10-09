import { useTranslation } from "react-i18next";
import type { Tracked } from "../lib/commands";
import { hasFeedback } from "../lib/contracts";

export function errorText(t: (k: string, o?: Record<string, unknown>) => string, code?: string, fallback?: string) {
  if (!code) return fallback ?? t("errors.generic");
  return t(`errors.${code}`, { defaultValue: fallback ?? t("errors.generic") });
}

const STEPS = ["queued", "sent", "acked", "confirmed"] as const;
// Index of the step already REACHED (-1 = request still on its way).
const REACHED: Record<string, number> = { sending: -1, queued: 0, sent: 1, acked: 2, confirmed: 3 };

/** Live progress of the REAL command lifecycle: Navbat → Hub → Qurilma → Tasdiq. */
export function CommandStatus({ tracked, compact = false }: { tracked: Tracked | null; compact?: boolean }) {
  const { t } = useTranslation();
  if (!tracked) return null;
  if (tracked.status === "error") {
    return <p className="error" role="alert">{errorText(t, tracked.error?.code, tracked.error?.message)}</p>;
  }
  if (compact) {
    // On a tile: a thin progress line; words only when it did not work.
    const bad = ["rejected", "failed", "expired", "timeout"].includes(tracked.status);
    const fin = tracked.status === "confirmed" || (tracked.status === "acked" && !hasFeedback(tracked.capability, tracked.action));
    const pct = bad || fin ? 100 : ((REACHED[tracked.status] ?? -1) + 2) * 20;
    return (
      <div className={`cmd-line ${bad ? "bad" : fin ? "ok" : ""}`} role="status" data-testid="command-status"
        data-status={tracked.status} title={t(`command.${tracked.status}`, { defaultValue: tracked.status })}>
        <i style={{ width: `${pct}%` }} />
        {bad && <span className="error">{t(`command.${tracked.status}`)}{tracked.reason ? ` (${tracked.reason})` : ""}</span>}
      </div>
    );
  }
  const failed = ["rejected", "failed", "expired", "timeout"].includes(tracked.status);
  const finalAck = tracked.status === "acked" && !hasFeedback(tracked.capability, tracked.action);
  const done = tracked.status === "confirmed" || finalAck;
  const reached = REACHED[tracked.status] ?? 0;
  const label = tracked.status === "sending" ? t("command.sending")
    : t(`command.${tracked.status}`) + (tracked.reason ? ` (${tracked.reason})` : "");
  const steps = finalAck ? STEPS.slice(0, 3) : STEPS;
  return (
    <div className={`steps ${failed ? "failed" : done ? "ok" : ""}`} role="status"
      data-testid="command-status" data-status={tracked.status}>
      <ol style={{ gridTemplateColumns: `repeat(${steps.length}, 1fr)` }}>
        {steps.map((s, i) => (
          <li key={s} className={failed ? "" : i <= reached ? "done" : !done && i === reached + 1 ? "now" : ""}>
            <i />
            <span>{t(`step.${s}`)}</span>
          </li>
        ))}
      </ol>
      <span className={failed ? "error" : "muted"}>{label}</span>
    </div>
  );
}
