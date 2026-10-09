/**
 * Yandex Alisa link (ADR 0016): paste the OAuth token once; Alisa's lights, sockets, TVs and
 * air conditioners then appear as devices. The token is never shown again (write-only).
 */
import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../api/client";
import { can } from "../lib/contracts";
import { useCurrentHome } from "../lib/home";
import { errorText } from "./CommandStatus";
import { Icon } from "./Icon";

interface Link {
  kind: "yandex"; status: "not_connected" | "pending" | "ok" | "error"; error?: string | null;
  last_sync?: string | null; scenarios?: { id: string; name: string }[]; skipped?: { name: string; type: string }[];
}

export function AlisaSettings() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { home } = useCurrentHome();
  const hid = home?.id;
  const link = useQuery({ queryKey: ["alisa", hid], enabled: !!hid,
    queryFn: () => api.get<Link>(`/homes/${hid}/integrations/yandex`) });
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const canEdit = can(home?.my_role, "configure");
  const l = link.data;

  const act = async (fn: () => Promise<unknown>, ok?: string) => {
    setBusy(true); setMsg(null);
    try {
      await fn();
      if (ok) setMsg({ ok: true, text: ok });
      void qc.invalidateQueries({ queryKey: ["alisa", hid] });
      void qc.invalidateQueries({ queryKey: ["devices", hid] });
    } catch (e) {
      setMsg({ ok: false, text: errorText(t, e instanceof ApiError ? e.code : "NETWORK", e instanceof Error ? e.message : undefined) });
    } finally { setBusy(false); }
  };

  return (
    <section className="card" aria-label={t("alisa.title")} data-testid="alisa">
      <div className="row spread">
        <h3 style={{ display: "flex", alignItems: "center", gap: 8 }}><Icon name="speaker" size={20} /> {t("alisa.title")}</h3>
        {l && l.status !== "not_connected" && (
          <span className={`badge ${l.status === "ok" ? "ok" : l.status === "error" ? "failed" : "pending"}`}>
            <span className="dot" />{t(`alisa.status.${l.status}`)}
          </span>
        )}
      </div>
      <p className="muted" style={{ margin: 0 }}>{t("alisa.intro")}</p>
      {l?.status === "error" && <p className="error" role="alert" style={{ margin: 0 }}>{t("alisa.error")}: {l.error}</p>}
      {l?.last_sync && <p className="muted" style={{ margin: 0 }}>{t("alisa.lastSync", { time: new Date(l.last_sync).toLocaleString() })}</p>}

      {canEdit && (!l || l.status === "not_connected" || l.status === "error") && (
        <form className="form" onSubmit={(e) => { e.preventDefault(); void act(() => api.put(`/homes/${hid}/integrations/yandex`, { token: token.trim() }), t("alisa.connected")).then(() => setToken("")); }}>
          <p className="note"><Icon name="alert" size={18} /> {t("alisa.howTo")}</p>
          <label>{t("alisa.token")}
            <input type="password" autoComplete="off" value={token} onChange={(e) => setToken(e.target.value)} />
          </label>
          <button className="primary" type="submit" disabled={busy || token.trim().length < 20}>
            <Icon name="plus" size={18} /> {t("alisa.connect")}</button>
        </form>
      )}

      {l && (l.scenarios?.length ?? 0) > 0 && (
        <div style={{ display: "grid", gap: 8 }}>
          <strong>{t("alisa.scenarios")}</strong>
          <div className="chips wrap">
            {l.scenarios!.map((s) => (
              <button key={s.id} type="button" disabled={busy}
                onClick={() => void act(() => api.post(`/homes/${hid}/integrations/yandex/scenarios/${s.id}/run`, {}), t("alisa.started", { name: s.name }))}>
                <Icon name="play" size={16} /> {s.name}
              </button>
            ))}
          </div>
        </div>
      )}
      {l && (l.skipped?.length ?? 0) > 0 && (
        <p className="muted" style={{ margin: 0 }}>{t("alisa.skipped", { names: l.skipped!.map((s) => s.name).join(", ") })}</p>
      )}
      {msg && <p className={msg.ok ? "muted" : "error"} role={msg.ok ? "status" : "alert"}>{msg.text}</p>}
      {canEdit && l && l.status !== "not_connected" && (
        <div className="row">
          <button type="button" disabled={busy} onClick={() => void act(() => api.post(`/homes/${hid}/integrations/yandex/sync`, {}), t("alisa.synced"))}>
            <Icon name="wifi" size={16} /> {t("alisa.sync")}</button>
          <button type="button" className="ghost" disabled={busy}
            onClick={() => { if (window.confirm(t("alisa.disconnectConfirm"))) void act(() => api.del(`/homes/${hid}/integrations/yandex`)); }}>
            <Icon name="close" size={16} /> {t("alisa.disconnect")}</button>
        </div>
      )}
    </section>
  );
}
