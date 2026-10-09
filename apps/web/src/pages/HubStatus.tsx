import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../api/client";
import { qk, useHubs } from "../api/hooks";
import type { Hub } from "../api/types";
import { errorText } from "../components/CommandStatus";
import { Badge } from "../components/StatusBadge";
import { can } from "../lib/contracts";
import { useCurrentHome } from "../lib/home";

interface Created extends Hub { hub_token: string; signing_key_hex: string }

function Secret({ label, value }: { label: string; value: string }) {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  return (
    <label>{label}
      <div className="row">
        <input readOnly value={value} onFocus={(e) => e.target.select()} style={{ flex: 1, fontFamily: "monospace" }} />
        <button type="button" onClick={async () => { try { await navigator.clipboard.writeText(value); setCopied(true); } catch { /* select manually */ } }}>
          {copied ? t("hub.copied") : t("hub.copy")}
        </button>
      </div>
    </label>
  );
}

export function HubStatus() {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const { home } = useCurrentHome();
  const hubs = useHubs(home?.id);
  const [name, setName] = useState("Asosiy hub");
  const [created, setCreated] = useState<Created | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const canConfigure = can(home?.my_role, "configure");
  const refresh = () => qc.invalidateQueries({ queryKey: qk.hubs(home!.id) });
  const hasActive = (hubs.data ?? []).some((h) => h.status === "active");

  const create = async (e: React.FormEvent) => {
    e.preventDefault(); setErr(null);
    try { setCreated(await api.post<Created>(`/homes/${home!.id}/hubs`, { name })); await refresh(); }
    catch (x) { setErr(x instanceof ApiError ? errorText(t, x.code, x.message) : t("errors.generic")); }
  };

  if (hubs.isLoading) return <p>{t("app.loading")}</p>;
  return (
    <div style={{ display: "grid", gap: 16 }}>
      <h2 style={{ margin: 0 }}>{t("hub.title")}</h2>
      {created && (
        <section className="card" role="alert">
          <strong>{t("hub.created")}</strong>
          <Secret label={t("hub.token")} value={created.hub_token} />
          <Secret label={t("hub.key")} value={created.signing_key_hex} />
          <button onClick={() => setCreated(null)}>{t("app.close")}</button>
        </section>
      )}
      {!hubs.data?.length && <p className="muted">{t("hub.none")}</p>}
      <div className="grid">{(hubs.data ?? []).map((h) => (
        <article key={h.id} className="card">
          <div className="row spread"><h3>{h.name}</h3>
            {h.status === "revoked" ? <Badge kind="unknown" label={t("hub.revoked")} /> :
              <Badge kind={h.online ? "ok" : "failed"} label={t(h.online ? "hub.online" : "hub.offline")} />}
          </div>
          <div className="row spread"><span className="muted">{t("hub.lastSeen")}</span>
            <span>{h.last_seen ? new Date(h.last_seen).toLocaleString(i18n.language, { timeZone: home?.timezone }) : "—"}</span></div>
          <div className="row spread"><span className="muted">{t("hub.version")}</span><span>{h.version ?? "—"}</span></div>
          {h.status === "active" && <HubHealth h={h} />}
          {canConfigure && h.status === "active" && (
            <button className="danger" onClick={async () => {
              if (window.confirm(t("hub.revokeConfirm"))) { await api.post(`/hubs/${h.id}/revoke`); await refresh(); }
            }}>{t("hub.revoke")}</button>
          )}
        </article>))}
      </div>
      {canConfigure && !hasActive && (
        <form className="card" onSubmit={create}>
          <h3>{t("hub.add")}</h3>
          <label>{t("hub.name")}<input required maxLength={120} value={name} onChange={(e) => setName(e.target.value)} /></label>
          {err && <p className="error" role="alert">{err}</p>}
          <button className="primary" type="submit">{t("hub.add")}</button>
        </form>
      )}
    </div>
  );
}

/** What the hub reported about itself; nothing is shown as fine unless the hub said so. */
function HubHealth({ h }: { h: Hub }) {
  const { t } = useTranslation();
  const hh = h.health ?? {};
  const unknown = t("status.unknown");
  const pct = (v?: number, warn?: boolean) => v === undefined ? unknown : <span className={warn ? "error" : ""}>{v}%</span>;
  return (
    <>
      <div className="row spread"><span className="muted">{t("hub.broker")}</span>
        <span className={hh.mqtt_connected === false ? "error" : ""}>
          {hh.mqtt_connected === undefined ? unknown : t(hh.mqtt_connected ? "hub.brokerOk" : "hub.brokerDown")}</span></div>
      <div className="row spread"><span className="muted">{t("hub.dataDisk")}</span><span>{pct(hh.data_disk_pct, hh.data_disk_warning)}</span></div>
      {hh.disk_usage_pct !== undefined &&
        <div className="row spread"><span className="muted">{t("hub.nvrDisk")}</span><span>{pct(hh.disk_usage_pct, hh.disk_warning)}</span></div>}
      <div className="row spread"><span className="muted">{t("hub.outbox")}</span><span>{hh.outbox ?? unknown}</span></div>
    </>
  );
}
