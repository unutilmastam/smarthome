import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api } from "../api/client";
import { useAutomationRuns, useAutomations, useDevices } from "../api/hooks";
import type { Automation, AutomationRun } from "../api/types";
import { useCanConfigure } from "../components/AddFlow";
import { AutomationEditor } from "../components/AutomationEditor";
import { Icon } from "../components/Icon";
import { Sheet } from "../components/Sheet";
import { summary, triggerIcon } from "../lib/automation";
import { useCurrentHome } from "../lib/home";

const RESULT_TONE: Record<string, string> = { ok: "ok", partial: "pending", failed: "failed", skipped: "unknown" };

function RunBadge({ run }: { run: AutomationRun }) {
  const { t, i18n } = useTranslation();
  const { home } = useCurrentHome();
  const when = new Date(run.ts).toLocaleString(i18n.language, { timeZone: home?.timezone ?? "Asia/Tashkent",
    day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
  return (
    <span className={`badge ${RESULT_TONE[run.result]}`} data-testid="run-result">
      <span className="dot" aria-hidden="true" />{t(`auto.result.${run.result}`)}
      {run.reason ? ` · ${t(`auto.reason.${run.reason}`, { defaultValue: run.reason })}` : ""} · {when}
    </span>
  );
}

export function Automations() {
  const { t } = useTranslation();
  const { home } = useCurrentHome();
  const qc = useQueryClient();
  const list = useAutomations(home?.id);
  const devices = useDevices(home?.id, true);
  const canEdit = useCanConfigure();
  const [editing, setEditing] = useState<Automation | "new" | null>(null);
  const [history, setHistory] = useState<Automation | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  if (!home || list.isLoading) return <p>{t("app.loading")}</p>;
  const all = list.data ?? [];
  const toggle = async (a: Automation) => {
    setBusy(a.id); setErr(null);
    try { await api.patch(`/automations/${a.id}`, { enabled: !a.enabled }); }
    catch { setErr(t("auto.toggleFailed", { name: a.name })); }
    finally { setBusy(null); void qc.invalidateQueries({ queryKey: ["automations", home.id] }); }
  };
  return (
    <>
      <div className="page-head">
        <h2>{t("auto.title")}</h2>
        {canEdit && <button className="primary add-btn" onClick={() => setEditing("new")}><Icon name="plus" size={18} /> {t("auto.new")}</button>}
      </div>
      <p className="note"><Icon name="hub" size={18} /> {t("auto.onHub")}</p>
      {err && <p className="error" role="alert">{err}</p>}
      {!all.length ? (
        <div className="empty card">
          <span className="ico big"><Icon name="play" size={34} /></span>
          <p>{t("auto.empty")}</p>
          <p className="muted">{t("auto.example")}</p>
        </div>
      ) : (
        <div className="grid">
          {all.map((a) => (
            <article key={a.id} className={`card auto-card ${a.enabled ? "on" : "off"}`} data-testid={`automation-${a.name}`}>
              <div className="dev-head">
                <span className="ico"><Icon name={triggerIcon(a.definition)} size={24} /></span>
                <div className="meta">
                  <h3>{a.name}</h3>
                  <span className="muted">{a.enabled ? t("auto.enabled") : t("auto.disabled")}</span>
                </div>
                <button type="button" role="switch" aria-checked={a.enabled} aria-label={`${t("auto.enabled")}: ${a.name}`}
                  className="pswitch" data-state={a.enabled ? "on" : "off"} data-pending={busy === a.id}
                  disabled={!canEdit || busy === a.id} onClick={() => void toggle(a)}>
                  <span className="track" aria-hidden="true"><span className="lbl on">I</span><span className="lbl off">O</span>
                    <span className="knob"><Icon name="play" size={16} /></span></span>
                </button>
              </div>
              <p className="auto-summary">{summary(t, a.definition, devices.data ?? [])}</p>
              <div className="row spread">
                {a.last_run ? <RunBadge run={a.last_run} /> : <span className="muted">{t("auto.neverRan")}</span>}
                <div className="row">
                  <button type="button" className="ghost" onClick={() => setHistory(a)}><Icon name="clock" size={16} /> {t("auto.history")}</button>
                  {canEdit && <button type="button" className="icon-btn" aria-label={`${t("auto.edit")}: ${a.name}`} onClick={() => setEditing(a)}><Icon name="edit" size={18} /></button>}
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
      {canEdit && (
        <AutomationEditor open={editing !== null} onClose={() => setEditing(null)} home={home}
          devices={devices.data ?? []} automation={editing && editing !== "new" ? editing : undefined} />
      )}
      <RunHistory automation={history} onClose={() => setHistory(null)} />
    </>
  );
}

function RunHistory({ automation, onClose }: { automation: Automation | null; onClose: () => void }) {
  const { t } = useTranslation();
  const runs = useAutomationRuns(automation?.id);
  return (
    <Sheet open={!!automation} onClose={onClose} title={`${t("auto.history")}: ${automation?.name ?? ""}`}>
      {!runs.data?.length ? <p className="muted">{t("auto.noRuns")}</p> : (
        <ul className="events">
          {runs.data.map((r) => (
            <li key={r.id} className={`event sev-${r.result === "failed" ? "critical" : r.result === "ok" ? "info" : "warning"}`}>
              <span className="ico"><Icon name={r.result === "ok" ? "check" : r.result === "skipped" ? "clock" : "alert"} size={20} /></span>
              <div className="event-body">
                <strong>{r.trigger}</strong>
                <span className="muted">{r.actions.map((x) => x.type === "notify" ? `🔔 ${x.text}` : `${x.device ?? x.type} ${x.action ?? ""}: ${t(`auto.outcome.${x.outcome.split(":")[0]}`, { defaultValue: x.outcome })}`).join(" · ")}</span>
                <RunBadge run={r} />
              </div>
            </li>
          ))}
        </ul>
      )}
    </Sheet>
  );
}
