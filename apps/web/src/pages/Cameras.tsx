import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { api, ApiError } from "../api/client";
import type { Value } from "../api/types";
import { errorText } from "../components/CommandStatus";
import { Badge } from "../components/StatusBadge";
import { ValueView } from "../components/ValueView";
import { can } from "../lib/contracts";
import { useCurrentHome } from "../lib/home";

interface CameraView {
  id: string; name: string; frigate_name: string;
  status: Record<string, Value> | null;
  availability: { status: "online" | "offline" | "unknown" } | null;
}
interface Access { links: { tailscale?: string; lan?: string }; archive_allowed: boolean }

function CameraCard({ cam, canLive }: { cam: CameraView; canLive: boolean }) {
  const { t } = useTranslation();
  const [access, setAccess] = useState<Access | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const avail = cam.availability?.status ?? "unknown";
  const disk = cam.status?.disk_usage_pct;
  return (
    <article className="card" data-testid={`camera-${cam.frigate_name}`}>
      <div className="row spread"><h3>{cam.name}</h3>
        <Badge kind={avail === "online" ? "ok" : avail === "offline" ? "failed" : "unknown"} label={t(`availability.${avail}`)} />
      </div>
      {cam.status && Object.entries(cam.status).map(([a, v]) => <ValueView key={a} attr={a} label={t(`attr.${a}`)} value={v} />)}
      {typeof disk?.value === "number" && disk.value >= 85 && <p className="error">{t("cameras.diskWarning", { pct: disk.value })}</p>}
      {!canLive ? <p className="muted">{t("cameras.noAccess")}</p> : !access ? (
        <button className="primary" onClick={async () => {
          setErr(null);
          try { setAccess(await api.get<Access>(`/cameras/${cam.id}/access`)); }
          catch (e) { setErr(e instanceof ApiError ? errorText(t, e.code, e.message) : t("errors.generic")); }
        }}>{t("cameras.live")}</button>
      ) : (
        <div style={{ display: "grid", gap: 8 }}>
          {!access.links.tailscale && !access.links.lan && <p className="muted">{t("cameras.noLinks")}</p>}
          {access.links.tailscale && <a className="primary" href={access.links.tailscale} target="_blank" rel="noopener noreferrer">{t("cameras.viaTailscale")} ↗</a>}
          {access.links.lan && <a href={access.links.lan} target="_blank" rel="noopener noreferrer">{t("cameras.viaLan")} ↗</a>}
          <p className="muted" style={{ margin: 0 }}>{t("cameras.requires")}</p>
        </div>
      )}
      {err && <p className="error" role="alert">{err}</p>}
    </article>
  );
}

function AddCamera({ homeId }: { homeId: string }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [fname, setFname] = useState("");
  const [err, setErr] = useState<string | null>(null);
  return (
    <form className="card" onSubmit={async (e) => {
      e.preventDefault(); setErr(null);
      try {
        await api.post(`/homes/${homeId}/cameras`, { name, frigate_name: fname });
        setName(""); setFname("");
        await qc.invalidateQueries({ queryKey: ["cameras", homeId] });
      } catch (x) { setErr(x instanceof ApiError ? errorText(t, x.code, x.message) : t("errors.generic")); }
    }}>
      <h3>{t("cameras.add")}</h3>
      <label>{t("devices.name")}<input required maxLength={120} value={name} onChange={(e) => setName(e.target.value)} /></label>
      <label>{t("cameras.frigateName")}<input required pattern="[a-z][a-z0-9_]{1,40}" autoCapitalize="none" value={fname} onChange={(e) => setFname(e.target.value.trim())} /></label>
      {err && <p className="error" role="alert">{err}</p>}
      <button className="primary" type="submit">{t("app.add")}</button>
    </form>
  );
}

export function Cameras() {
  const { t } = useTranslation();
  const { home } = useCurrentHome();
  const cams = useQuery({ queryKey: ["cameras", home?.id ?? ""], enabled: !!home, refetchInterval: 30_000,
    queryFn: () => api.get<CameraView[]>(`/homes/${home!.id}/cameras`) });
  return (
    <div style={{ display: "grid", gap: 16 }}>
      <h2 style={{ margin: 0 }}>{t("cameras.title")}</h2>
      {cams.isLoading ? <p>{t("app.loading")}</p> : !cams.data?.length ? <p className="muted">{t("cameras.none")}</p> :
        <div className="grid">{cams.data.map((c) => <CameraCard key={c.id} cam={c} canLive={can(home?.my_role, "camera_live")} />)}</div>}
      {home && can(home.my_role, "configure") && <div style={{ maxWidth: 560 }}><AddCamera homeId={home.id} /></div>}
    </div>
  );
}
