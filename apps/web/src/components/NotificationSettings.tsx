import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../api/client";
import { useNotificationChannels, useNotifyPrefs } from "../api/hooks";
import type { TelegramLinkCode } from "../api/types";
import { useCurrentHome } from "../lib/home";
import { currentEndpoint, disablePush, enablePush, pushSupport } from "../lib/push";
import { errorText } from "./CommandStatus";
import { Icon } from "./Icon";

type Msg = { ok: boolean; text: string } | null;

/** Settings → Notifications (ADR 0014): Telegram link, Web Push on this device, level, test. */
export function NotificationSettings() {
  const { t, i18n } = useTranslation();
  const qc = useQueryClient();
  const { home } = useCurrentHome();
  const ch = useNotificationChannels();
  const { refetch } = ch;
  const prefs = useNotifyPrefs(home?.id);
  const [code, setCode] = useState<TelegramLinkCode | null>(null);
  const [endpoint, setEndpoint] = useState<string | null>(null);
  const [busy, setBusy] = useState("");
  const [msg, setMsg] = useState<Msg>(null);
  const support = pushSupport();

  useEffect(() => { void currentEndpoint().then(setEndpoint); }, []);
  useEffect(() => {
    if (window.location.hash === "#notifications") document.getElementById("notifications")?.scrollIntoView();
  }, []);
  // While a code is shown, look for the new link every 3 s (the bot confirms it in Telegram).
  useEffect(() => {
    if (!code) return;
    const id = setInterval(() => void refetch(), 3000);
    return () => clearInterval(id);
  }, [code, refetch]);
  const links = ch.data?.telegram.links ?? [];
  useEffect(() => { if (code && links.length) setCode(null); }, [code, links.length]);

  const run = async (name: string, fn: () => Promise<Msg | void>) => {
    setBusy(name); setMsg(null);
    try { const m = await fn(); if (m) setMsg(m); }
    catch (e) { setMsg({ ok: false, text: errorText(t, e instanceof ApiError ? e.code : "NETWORK") }); }
    finally { setBusy(""); void ch.refetch(); }
  };
  const registered = !!endpoint && (ch.data?.push.subscriptions ?? []).some((s) => s.endpoint === endpoint);
  const time = (iso: string) => new Date(iso).toLocaleTimeString(i18n.language, { hour: "2-digit", minute: "2-digit" });

  return (
    <section className="card" id="notifications" aria-labelledby="notify-h">
      <h3 id="notify-h">{t("notify.settings")}</h3>
      {prefs.data && !prefs.data.receives && <p className="muted">{t("notify.roleNone")}</p>}

      <div className="channel">
        <span className="ico"><Icon name="send" /></span>
        <div className="body">
          <strong>Telegram</strong>
          {!ch.data ? <span className="muted">{t("app.loading")}</span>
            : !ch.data.telegram.available ? <span className="muted">{t("notify.notConfigured")}</span> : (
            <>
              {links.map((l) => (
                <div key={l.id} className="row spread">
                  <span className="ok-text"><Icon name="check" size={16} /> {t("notify.tgLinked", { name: l.username ? "@" + l.username : "Telegram" })}</span>
                  <button className="small" disabled={!!busy} onClick={() => void run("unlink", async () => {
                    await api.del(`/notifications/telegram/links/${l.id}`);
                  })}>{t("notify.unlink")}</button>
                </div>
              ))}
              {code ? (
                <div className="body">
                  <span>{t("notify.tgStep")}</span>
                  {code.url && <a className="primary" href={code.url} target="_blank" rel="noreferrer"><Icon name="send" size={18} />&nbsp;{t("notify.tgOpen")}</a>}
                  <div className="link-code" aria-label={t("notify.tgCode")}>{code.code}</div>
                  <span className="muted">{t("notify.tgManual", { bot: code.bot_username ? "@" + code.bot_username : "bot", time: time(code.expires_at) })}</span>
                </div>
              ) : (
                <button className={links.length ? "" : "primary"} disabled={!!busy} onClick={() => void run("link", async () => {
                  setCode(await api.post<TelegramLinkCode>("/notifications/telegram/link"));
                })}>{t(links.length ? "notify.tgLinkMore" : "notify.tgLink")}</button>
              )}
            </>
          )}
        </div>
      </div>

      <div className="channel">
        <span className="ico"><Icon name="phone" /></span>
        <div className="body">
          <strong>{t("notify.push")}</strong>
          {!ch.data ? null
            : !ch.data.push.available ? <span className="muted">{t("notify.notConfigured")}</span>
            : support === "ios_install" ? <span className="muted">{t("notify.iosInstall")}</span>
            : support === "unsupported" ? <span className="muted">{t("notify.pushUnsupported")}</span>
            : registered ? (
              <div className="row spread">
                <span className="ok-text"><Icon name="check" size={16} /> {t("notify.pushOn")}</span>
                <button className="small" disabled={!!busy} onClick={() => void run("push-off", async () => {
                  await disablePush(); setEndpoint(null);
                })}>{t("notify.pushDisable")}</button>
              </div>
            ) : (
              <button className="primary" disabled={!!busy} onClick={() => void run("push-on", async () => {
                const r = await enablePush(ch.data!.push.public_key!);
                if (r === "denied") return { ok: false, text: t("notify.pushDenied") };
                setEndpoint(await currentEndpoint());
              })}>{t("notify.pushEnable")}</button>
            )}
          {(ch.data?.push.subscriptions.length ?? 0) > (registered ? 1 : 0) &&
            <span className="muted">{t("notify.pushOther", { count: (ch.data?.push.subscriptions.length ?? 0) - (registered ? 1 : 0) })}</span>}
        </div>
      </div>

      {home && prefs.data?.receives && (
        <label>{t("notify.level")}
          <select value={prefs.data.notify_min_severity} disabled={!!busy} onChange={(e) => void run("prefs", async () => {
            await api.put(`/homes/${home.id}/notification-prefs`, { notify_min_severity: e.target.value });
            await qc.invalidateQueries({ queryKey: ["notify-prefs"] });
          })}>
            <option value="info">{t("notify.levelInfo")}</option>
            <option value="warning">{t("notify.levelWarning")}</option>
            <option value="critical">{t("notify.levelCritical")}</option>
          </select>
        </label>
      )}
      {home && (
        <button disabled={!!busy} onClick={() => void run("test", async () => {
          const r = await api.post<{ deliveries: { channel: string; status: string }[] }>(`/homes/${home.id}/notifications:test`);
          if (!r.deliveries.length) return { ok: false, text: t("notify.testNone") };
          return {
            ok: r.deliveries.every((d) => d.status === "sent"),
            text: r.deliveries.map((d) => `${d.channel === "push" ? t("notify.push") : "Telegram"}: ${t(`notify.status.${d.status}`, { defaultValue: d.status })}`).join(" · "),
          };
        })}><Icon name="bell" size={16} /> {t("notify.test")}</button>
      )}
      {msg && <p className={msg.ok ? "muted" : "error"} role={msg.ok ? "status" : "alert"}>{msg.text}</p>}
    </section>
  );
}
