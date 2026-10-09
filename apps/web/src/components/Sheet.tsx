import { useEffect, useId, useRef, type ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Icon } from "./Icon";

/** Bottom sheet on phones, centered dialog on tablets/desktop. Esc and backdrop close it. */
export function Sheet({ open, title, onClose, children, onBack }: {
  open: boolean; title: string; onClose: () => void; children: ReactNode; onBack?: () => void;
}) {
  const { t } = useTranslation();
  const id = useId();
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement as HTMLElement | null;
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    ref.current?.querySelector<HTMLElement>("input, select, button.tile, button.primary")?.focus();
    return () => { document.removeEventListener("keydown", onKey); prev?.focus?.(); };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="sheet-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div className="sheet" role="dialog" aria-modal="true" aria-labelledby={id} ref={ref}>
        <div className="sheet-grip" aria-hidden="true" />
        <header className="sheet-head">
          {onBack && <button type="button" className="icon-btn" aria-label={t("app.back")} onClick={onBack}><Icon name="back" /></button>}
          <h2 id={id}>{title}</h2>
          <button type="button" className="icon-btn" aria-label={t("app.close")} onClick={onClose}><Icon name="close" /></button>
        </header>
        <div className="sheet-body">{children}</div>
      </div>
    </div>
  );
}

/** Grid of selectable icons (radio group). */
export function IconPicker({ icons, value, onChange, label, labelFor }: {
  icons: string[]; value: string; onChange: (v: string) => void; label: string; labelFor: (icon: string) => string;
}) {
  return (
    <fieldset className="icon-picker">
      <legend>{label}</legend>
      <div role="radiogroup" aria-label={label}>
        {icons.map((ic) => (
          <button key={ic} type="button" role="radio" aria-checked={value === ic} aria-label={labelFor(ic)}
            title={labelFor(ic)} onClick={() => onChange(ic)}>
            <Icon name={ic} size={22} />
          </button>
        ))}
      </div>
    </fieldset>
  );
}
