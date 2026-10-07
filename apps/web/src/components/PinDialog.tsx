import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

/** Asks for the PIN before a high-risk action (ARCHITECTURE 9). The PIN is never stored. */
export function PinDialog({ open, action, onSubmit, onCancel }: {
  open: boolean; action: string; onSubmit: (pin: string) => void; onCancel: () => void;
}) {
  const { t } = useTranslation();
  const [pin, setPin] = useState("");
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (open && !d.open) { setPin(""); d.showModal?.() ?? d.setAttribute("open", ""); }
    if (!open && d.open) { d.close?.() ?? d.removeAttribute("open"); }
  }, [open]);
  if (!open) return <dialog ref={ref} />;
  const valid = /^\d{4,8}$/.test(pin);
  return (
    <dialog ref={ref} aria-labelledby="pin-title" onCancel={(e) => { e.preventDefault(); onCancel(); }}>
      <form method="dialog" onSubmit={(e) => { e.preventDefault(); if (valid) onSubmit(pin); }} style={{ display: "grid", gap: 12 }}>
        <h3 id="pin-title" style={{ margin: 0 }}>{t("control.pinTitle")}</h3>
        <p className="muted" style={{ margin: 0 }}>{t("control.pinHint", { action })}</p>
        <label>{t("control.pin")}
          <input autoFocus inputMode="numeric" autoComplete="off" type="password" maxLength={8}
            value={pin} onChange={(e) => setPin(e.target.value.replace(/\D/g, ""))} aria-label={t("control.pin")} />
        </label>
        <div className="row spread">
          <button type="button" onClick={onCancel}>{t("app.cancel")}</button>
          <button type="submit" className="primary" disabled={!valid}>{t("control.confirm")}</button>
        </div>
      </form>
    </dialog>
  );
}
