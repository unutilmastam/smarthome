import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { BreakerPanels } from "../components/BreakerPanel";
import { api, ApiError } from "../api/client";
import { qk, useDevices, useEnergy, useTelemetry } from "../api/hooks";
import type { Device, EnergySummary } from "../api/types";
import { errorText } from "../components/CommandStatus";
import { useLive } from "../components/Layout";
import { Sparkline } from "../components/Sparkline";
import { ValueView } from "../components/ValueView";
import { can } from "../lib/contracts";
import { useCurrentHome } from "../lib/home";

function fmtNum(n: number | null | undefined, digits = 2) {
  return n === null || n === undefined ? "—" : n.toLocaleString(undefined, { maximumFractionDigits: digits });
}

function Totals({ title, s }: { title: string; s?: EnergySummary }) {
  const { t } = useTranslation();
  const partial = s?.devices.some((d) => s.period === "month" && d.days_with_data < 1);
  return (
    <article className="card" data-testid={`energy-${s?.period ?? "x"}`}>
      <h3>{title}</h3>
      <div className="value">{s?.total_kwh === null || s?.total_kwh === undefined ? t("energy.noData") : `${fmtNum(s.total_kwh, 3)} ${t("energy.kwh")}`}</div>
      <div className="muted">{t("energy.cost")}: {s?.total_cost === null || s?.total_cost === undefined
        ? (s?.tariff_per_kwh === null ? t("energy.noTariff") : "—")
        : `${fmtNum(s.total_cost)} ${s.currency}`}</div>
      {partial && <div className="muted">{t("energy.partial")}</div>}
    </article>
  );
}

function MeterCard({ device }: { device: Device }) {
  const { t } = useTranslation();
  const pm = device.capabilities.power_meter;
  const series = useTelemetry(device.id);
  return (
    <article className="card">
      <h3>{device.name}</h3>
      {Object.entries(pm.attributes).map(([a, v]) => <ValueView key={a} label={t(`attr.${a}`)} value={v} big={a === "power"} />)}
      <div className="muted">{t("energy.power24h")}</div>
      {series.data && series.data.length > 1 ? <Sparkline points={series.data} unit="W" /> : <p className="muted">{t("energy.noData")}</p>}
    </article>
  );
}

function TariffForm({ homeId, tariff, currency }: { homeId: string; tariff: number | null; currency: string }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [value, setValue] = useState(tariff === null ? "" : String(tariff));
  const [cur, setCur] = useState(currency);
  const [msg, setMsg] = useState<string | null>(null);
  return (
    <form className="card" onSubmit={async (e) => {
      e.preventDefault(); setMsg(null);
      try {
        await api.patch(`/homes/${homeId}`, { tariff_per_kwh: value === "" ? null : Number(value), currency: cur });
        await qc.invalidateQueries({ queryKey: qk.homes });
        await qc.invalidateQueries({ queryKey: ["energy", homeId] });
        setMsg("✓");
      } catch (x) { setMsg(x instanceof ApiError ? errorText(t, x.code, x.message) : t("errors.generic")); }
    }}>
      <label>{t("energy.tariff")}<input type="number" min={0} step="any" inputMode="decimal" value={value} onChange={(e) => setValue(e.target.value)} /></label>
      <label>{t("energy.currency")}<input maxLength={3} value={cur} onChange={(e) => setCur(e.target.value.toUpperCase())} pattern="[A-Z]{3}" /></label>
      {msg && <p className="muted" role="status">{msg}</p>}
      <button className="primary" type="submit">{t("app.save")}</button>
    </form>
  );
}

export function Energy() {
  const { t } = useTranslation();
  const { home } = useCurrentHome();
  const day = useEnergy(home?.id, "day");
  const month = useEnergy(home?.id, "month");
  const devices = useDevices(home?.id, useLive());
  const meters = (devices.data ?? []).filter((d) => "power_meter" in d.capabilities);
  const contactors = (devices.data ?? []).filter((d) => "contactor" in d.capabilities);
  // Breakers with metering show their power on the panel, not again as a separate meter card.
  const plainMeters = meters.filter((d) => !d.capabilities.breaker);
  return (
    <div style={{ display: "grid", gap: 16 }}>
      <h2 style={{ margin: 0 }}>{t("energy.title")}</h2>
      <div className="grid">
        <Totals title={t("energy.today")} s={day.data} />
        <Totals title={t("energy.month")} s={month.data} />
      </div>
      <h3 style={{ margin: 0 }}>{t("panel.title")}</h3>
      <BreakerPanels devices={devices.data ?? []} role={home?.my_role} />
      <h3 style={{ margin: 0 }}>{t("energy.meters")}</h3>
      {plainMeters.length === 0 ? <p className="muted">{t("energy.noMeters")}</p> :
        <div className="grid">{plainMeters.map((d) => <MeterCard key={d.id} device={d} />)}</div>}
      {contactors.length > 0 && <p className="muted">{t("energy.breakerNote")}</p>}
      {home && can(home.my_role, "configure") &&
        <div style={{ maxWidth: 420 }}><TariffForm homeId={home.id} tariff={home.tariff_per_kwh} currency={home.currency} /></div>}
    </div>
  );
}
