import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../api/client";
import type { Device } from "../api/types";
import { can } from "../lib/contracts";
import { useCurrentHome } from "../lib/home";
import { errorText } from "./CommandStatus";
import { Icon } from "./Icon";

const isOpen = (d: Device) => {
  const v = d.capabilities.valve?.attributes.open;
  return !!v && (v.quality === "good" || v.quality === "stale") && v.value === true;
};

/**
 * Emergency stop for irrigation: one tap sends a signed "close" to every valve that REPORTS
 * open. The physical emergency button and max_runtime in the firmware work without this.
 */
export function IrrigationStop({ devices }: { devices: Device[] }) {
  const { t } = useTranslation();
  const { home } = useCurrentHome();
  const qc = useQueryClient();
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const open = devices.filter(isOpen);
  if (!open.length || !can(home?.my_role, "control_basic")) return null;
  const stopAll = async () => {
    setBusy(true); setMsg(null);
    const results = await Promise.allSettled(open.map((d) => api.post("/commands", {
      device_id: d.id, capability: "valve", action: "close", params: {},
      idempotency_key: `stop-${d.id}-${Date.now()}`,
    })));
    const failed = results.filter((r) => r.status === "rejected") as PromiseRejectedResult[];
    setBusy(false);
    void qc.invalidateQueries({ queryKey: ["devices", home?.id ?? ""] });
    if (failed.length) {
      const e = failed[0].reason;
      setMsg({ ok: false, text: e instanceof ApiError ? errorText(t, e.code, e.message) : t("errors.generic") });
    } else setMsg({ ok: true, text: t("irrigation.stopSent", { count: open.length }) });
  };
  return (
    <div className="banner danger-banner" role="status" data-testid="irrigation-stop">
      <Icon name="sprinkler" />
      <span style={{ flex: 1 }}>{t("irrigation.running", { names: open.map((d) => d.name).join(", ") })}</span>
      <button className="danger" disabled={busy} onClick={() => void stopAll()}>
        <Icon name="stop" size={18} /> {t("irrigation.stopAll")}
      </button>
      {msg && <span className={msg.ok ? "muted" : "error"} role={msg.ok ? undefined : "alert"}>{msg.text}</span>}
    </div>
  );
}
