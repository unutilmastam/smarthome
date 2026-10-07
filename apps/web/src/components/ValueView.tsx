import { useTranslation } from "react-i18next";
import type { Value } from "../api/types";
import { formatValue } from "../lib/status";
import { ValueBadge } from "./StatusBadge";

export function ValueView({ label, value, pending, big = false, attr }: {
  label: string; value?: Value; pending?: boolean; big?: boolean; attr?: string;
}) {
  const { t } = useTranslation();
  const known = value && (value.quality === "good" || value.quality === "stale");
  return (
    <div className="row spread" data-testid={`value-${label}`}>
      <span className="muted">{label}</span>
      <span className="row">
        <span className={`${big ? "value" : ""} ${known ? "" : "dim"}`}>{formatValue(value, t, attr)}</span>
        <ValueBadge value={value} pending={pending} />
      </span>
    </div>
  );
}
