import { useState } from "react";
import { useTranslation } from "react-i18next";
import { ApiError } from "../api/client";
import { useSession } from "../auth/session";
import { Icon } from "../components/Icon";

export function Login() {
  const { t } = useTranslation();
  const login = useSession((s) => s.login);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true); setError(null);
    try { await login(email, password); }
    catch (err) {
      const code = err instanceof ApiError ? err.code : "";
      setError(code === "INVALID_CREDENTIALS" ? t("login.invalid") : code === "RATE_LIMITED" ? t("login.locked") : t("login.failed"));
    } finally { setBusy(false); }
  };

  return (
    <main className="login">
      <form className="card" onSubmit={submit}>
        <span className="brand-mark"><Icon name="home" size={28} /></span>
        <div>
          <h2 style={{ margin: 0 }}>{t("login.title")}</h2>
          <p className="muted" style={{ margin: "4px 0 0" }}>{t("login.subtitle")}</p>
        </div>
        <label>{t("login.email")}<input type="email" autoComplete="username" required value={email} onChange={(e) => setEmail(e.target.value)} /></label>
        <label>{t("login.password")}<input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} /></label>
        {error && <p className="error" role="alert">{error}</p>}
        <button className="primary" type="submit" disabled={busy}>{t("login.submit")}</button>
      </form>
    </main>
  );
}
